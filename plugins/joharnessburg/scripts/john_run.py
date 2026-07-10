#!/usr/bin/env python3
"""Durable, provider-neutral run ledger for John vertical work."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from john_paths import find_john_root
from path_safety import (
    atomic_write_text,
    ensure_contained,
    reject_tree_symlinks,
    validate_work_id,
)


SCHEMA_VERSION = "john.run.v1"
DEFAULT_CONCURRENCY = 6
DEFAULT_TIMEOUT = 1800
DEFAULT_MAX_ATTEMPTS = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def emit(payload: dict, *, success: bool = True, exit_code: int = 0) -> None:
    payload["success"] = success
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    raise SystemExit(exit_code)


def fail(message: str, *, exit_code: int = 1) -> None:
    sys.stderr.write(message + "\n")
    emit({"error": message}, success=False, exit_code=exit_code)


def read_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def project_root() -> Path:
    root = find_john_root(Path.cwd())
    if root is None:
        raise ValueError(f"No .john/ directory found at or above {Path.cwd()}")
    return root


def run_dir(root: Path, phase: str, run_id: str) -> Path:
    validate_work_id(phase, field="phase")
    validate_work_id(run_id, field="run_id")
    runs = root / ".john" / "runs"
    phase_dir = ensure_contained(runs, runs / phase, label="run phase directory")
    return ensure_contained(phase_dir, phase_dir / run_id, label="run directory")


def load_run(root: Path, phase: str, run_id: str) -> tuple[Path, dict]:
    directory = run_dir(root, phase, run_id)
    reject_tree_symlinks(directory, label="run ledger")
    manifest = read_object(directory / "manifest.json")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported run schema in {directory / 'manifest.json'}")
    if manifest.get("phase") != phase or manifest.get("run_id") != run_id:
        raise ValueError("manifest identity does not match its path")
    return directory, manifest


def csv_rows(path: Path, id_column: str) -> tuple[list[str], list[dict[str, str]], str]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("work CSV must be UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or id_column not in reader.fieldnames:
        raise ValueError(f"work CSV must contain {id_column!r} column")
    rows = list(reader)
    if not rows:
        raise ValueError("work CSV must contain at least one item")
    ids: list[str] = []
    for row_number, row in enumerate(rows, start=2):
        item_id = validate_work_id(row.get(id_column), field=f"row {row_number} item_id")
        if item_id in ids:
            raise ValueError(f"duplicate item_id in work CSV: {item_id}")
        ids.append(item_id)
    canonical_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(canonical_buffer, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return reader.fieldnames, rows, canonical_buffer.getvalue()


def command_create(args: argparse.Namespace, root: Path) -> dict:
    directory = run_dir(root, args.phase, args.run_id)
    for field in ("stage", "provider", "engine", "worker_role", "terminal_event"):
        validate_work_id(getattr(args, field), field=field)
    validate_work_id(args.item_id_column, field="item_id_column")
    source = Path(args.work_csv).expanduser().resolve()
    if not source.is_file() or source.is_symlink():
        raise ValueError(f"work CSV must be a regular file: {source}")
    fields, rows, canonical_csv = csv_rows(source, args.item_id_column)
    checksum = "sha256:" + hashlib.sha256(canonical_csv.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "phase": args.phase,
        "stage": args.stage,
        "created_at": now(),
        "provider": args.provider,
        "engine": args.engine,
        "worker_role": args.worker_role,
        "item_id_column": args.item_id_column,
        "work_fields": fields,
        "work_count": len(rows),
        "work_checksum": checksum,
        "required_terminal_event": args.terminal_event,
        "policy": {
            "max_depth": args.max_depth,
            "concurrency": args.concurrency,
            "per_worker_timeout_seconds": args.timeout,
            "max_attempts": args.max_attempts,
        },
        "item_ids": [row[args.item_id_column] for row in rows],
    }
    if directory.exists():
        existing = read_object(directory / "manifest.json")
        immutable_fields = (
            "phase",
            "stage",
            "provider",
            "engine",
            "worker_role",
            "item_id_column",
            "work_fields",
            "work_count",
            "work_checksum",
            "required_terminal_event",
            "policy",
            "item_ids",
        )
        comparable = all(existing.get(field) == manifest[field] for field in immutable_fields)
        if not comparable:
            raise ValueError(f"run already exists with different immutable input: {directory}")
        return {"created": False, "run_dir": str(directory.relative_to(root)), "manifest": existing}

    directory.parent.mkdir(parents=True, exist_ok=True)
    stage = directory.parent / f".{directory.name}.stage-{hashlib.sha256(now().encode()).hexdigest()[:12]}"
    try:
        stage.mkdir()
        (stage / "attempts").mkdir()
        atomic_write_text(stage / "work.csv", canonical_csv)
        atomic_write_text(stage / "manifest.json", json.dumps(manifest, indent=2) + "\n")
        stage.rename(directory)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    return {"created": True, "run_dir": str(directory.relative_to(root)), "manifest": manifest}


def normalized_event_files(root: Path, values: list[str]) -> list[str]:
    event_root = root / ".john" / "events"
    normalized: list[str] = []
    for value in values:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = ensure_contained(event_root, candidate, label="receipt event file")
        normalized.append(str(resolved.relative_to(root)))
    return normalized


def command_record(args: argparse.Namespace, root: Path) -> dict:
    directory, manifest = load_run(root, args.phase, args.run_id)
    validate_work_id(args.item_id, field="item_id")
    validate_work_id(args.attempt_id, field="attempt_id")
    for field in ("provider", "engine", "worker"):
        validate_work_id(getattr(args, field), field=field)
    if args.item_id not in manifest["item_ids"]:
        raise ValueError(f"item_id is not in immutable work input: {args.item_id}")
    started = args.started_at or now()
    finished = args.finished_at or now()
    if parse_timestamp(finished, "finished_at") < parse_timestamp(started, "started_at"):
        raise ValueError("finished_at may not precede started_at")
    event_files = normalized_event_files(root, args.event_file)
    error = None
    if args.error_json:
        error = json.loads(args.error_json)
        if not isinstance(error, dict):
            raise ValueError("--error-json must be one JSON object")
    if args.status == "succeeded" and not event_files:
        raise ValueError("succeeded attempts must reference at least one event file")
    if args.status != "succeeded" and error is None:
        raise ValueError("non-succeeded attempts require structured --error-json")
    receipt = {
        "schema_version": "john.attempt.v1",
        "run_id": args.run_id,
        "phase": args.phase,
        "stage": manifest.get("stage"),
        "item_id": args.item_id,
        "attempt_id": args.attempt_id,
        "provider": args.provider,
        "engine": args.engine,
        "worker": args.worker,
        "started_at": started,
        "finished_at": finished,
        "status": args.status,
        "event_files": event_files,
        "error": error,
    }
    item_dir = ensure_contained(
        directory / "attempts",
        directory / "attempts" / args.item_id,
        label="item attempts directory",
    )
    path = ensure_contained(item_dir, item_dir / f"{args.attempt_id}.json", label="attempt receipt")
    if path.exists():
        existing = read_object(path)
        if args.started_at is None:
            receipt["started_at"] = existing.get("started_at")
        if args.finished_at is None:
            receipt["finished_at"] = existing.get("finished_at")
        if existing != receipt:
            raise ValueError(f"attempt_id already exists with different receipt: {args.attempt_id}")
        return {"recorded": False, "receipt": existing, "receipt_file": str(path.relative_to(root))}
    item_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(receipt, indent=2) + "\n")
    return {"recorded": True, "receipt": receipt, "receipt_file": str(path.relative_to(root))}


def receipts_for(directory: Path, item_id: str) -> list[dict]:
    item_dir = directory / "attempts" / item_id
    receipts: list[dict] = []
    if item_dir.is_dir():
        for path in sorted(item_dir.glob("*.json")):
            receipt = read_object(path)
            receipt["_receipt_file"] = str(path)
            receipts.append(receipt)
    return receipts


def event_identity(event: dict, key: str) -> object:
    if key in event:
        return event[key]
    payload = event.get("payload")
    return payload.get(key) if isinstance(payload, dict) else None


def verify_receipt(root: Path, manifest: dict, item_id: str, receipt: dict) -> list[str]:
    reasons: list[str] = []
    required = manifest["required_terminal_event"]
    terminal_found = False
    if receipt.get("run_id") != manifest["run_id"] or receipt.get("item_id") != item_id:
        return ["receipt identity mismatch"]
    event_root = root / ".john/events"
    try:
        reject_tree_symlinks(event_root, label="event ledger")
    except ValueError as exc:
        return [str(exc)]
    for relative in receipt.get("event_files") or []:
        try:
            path = ensure_contained(
                root / ".john/events", root / relative, label="referenced event"
            )
        except ValueError as exc:
            reasons.append(str(exc))
            continue
        if not path.is_file() or path.is_symlink():
            reasons.append(f"missing event file: {relative}")
            continue
        try:
            event = read_object(path)
        except ValueError as exc:
            reasons.append(str(exc))
            continue
        if event_identity(event, "run_id") != manifest["run_id"]:
            reasons.append(f"event run_id mismatch: {relative}")
        if event_identity(event, "item_id") != item_id:
            reasons.append(f"event item_id mismatch: {relative}")
        if event.get("event_type") == required:
            terminal_found = True
    if not terminal_found:
        reasons.append(f"required terminal event not found: {required}")
    return reasons


def compute_reconciliation(root: Path, directory: Path, manifest: dict) -> dict:
    control_path = directory / "control.json"
    control = read_object(control_path) if control_path.is_file() else {"cancelled": False}
    max_attempts = manifest["policy"]["max_attempts"]
    items: list[dict] = []
    for item_id in manifest["item_ids"]:
        receipts = receipts_for(directory, item_id)
        valid_receipts: list[dict] = []
        malformed_reasons: list[str] = []
        seen_attempts: set[str] = set()
        for receipt in receipts:
            attempt_id = receipt.get("attempt_id")
            if (
                receipt.get("run_id") != manifest["run_id"]
                or receipt.get("item_id") != item_id
                or not isinstance(attempt_id, str)
                or attempt_id in seen_attempts
            ):
                malformed_reasons.append("malformed or duplicate attempt receipt")
                continue
            try:
                parse_timestamp(receipt.get("finished_at"), "finished_at")
            except ValueError as exc:
                malformed_reasons.append(str(exc))
                continue
            seen_attempts.add(attempt_id)
            valid_receipts.append(receipt)
        latest = max(
            valid_receipts,
            key=lambda receipt: (
                parse_timestamp(receipt["finished_at"], "finished_at"),
                receipt["attempt_id"],
            ),
            default=None,
        )
        artifact_reasons: list[str] = []
        if control.get("cancelled") and latest is None:
            status = "cancelled"
        elif latest is None:
            status = "pending"
        elif latest.get("status") == "succeeded":
            artifact_reasons = verify_receipt(root, manifest, item_id, latest)
            status = "completed" if not artifact_reasons else "invalid_artifacts"
        else:
            status = latest.get("status") or "malformed"
        attempts = len(valid_receipts)
        retryable = (
            not control.get("cancelled")
            and status not in {"completed", "cancelled"}
            and attempts < max_attempts
        )
        items.append(
            {
                "item_id": item_id,
                "status": status,
                "attempt_count": attempts,
                "latest_attempt_id": latest.get("attempt_id") if latest else None,
                "event_files": latest.get("event_files", []) if latest else [],
                "artifact_verified": status == "completed",
                "reasons": malformed_reasons + artifact_reasons,
                "error": latest.get("error") if latest else None,
                "retryable": retryable,
            }
        )
    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    if control.get("cancelled"):
        run_status = "cancelled"
    elif counts.get("completed", 0) == len(items):
        run_status = "complete"
    elif any(not item["retryable"] and item["status"] != "completed" for item in items):
        run_status = "failed"
    else:
        run_status = "in_progress"
    return {
        "schema_version": "john.reconciliation.v1",
        "run_id": manifest["run_id"],
        "phase": manifest["phase"],
        "stage": manifest.get("stage"),
        "status": run_status,
        "cancelled": bool(control.get("cancelled")),
        "generated_at": now(),
        "expected_items": len(items),
        "counts": dict(sorted(counts.items())),
        "items": items,
    }


def command_reconcile(args: argparse.Namespace, root: Path, *, write: bool = True) -> dict:
    directory, manifest = load_run(root, args.phase, args.run_id)
    reconciliation = compute_reconciliation(root, directory, manifest)
    if write:
        existing_path = directory / "reconciliation.json"
        if existing_path.is_file():
            existing = read_object(existing_path)
            old_comparable = {k: v for k, v in existing.items() if k != "generated_at"}
            new_comparable = {k: v for k, v in reconciliation.items() if k != "generated_at"}
            if old_comparable == new_comparable:
                reconciliation = existing
        atomic_write_text(
            existing_path,
            json.dumps(reconciliation, indent=2) + "\n",
        )
    return {"run_dir": str(directory.relative_to(root)), "reconciliation": reconciliation}


def command_retry_csv(args: argparse.Namespace, root: Path) -> dict:
    directory, manifest = load_run(root, args.phase, args.run_id)
    reconciliation = compute_reconciliation(root, directory, manifest)
    retry_ids = {item["item_id"] for item in reconciliation["items"] if item["retryable"]}
    work_path = directory / "work.csv"
    with work_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [row for row in reader if row[manifest["item_id_column"]] in retry_ids]
        fields = reader.fieldnames or []
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    output = Path(args.output).expanduser() if args.output else directory / "retry.csv"
    if not output.is_absolute():
        output = root / output
    output = ensure_contained(root, output, label="retry CSV")
    atomic_write_text(output, buffer.getvalue())
    return {
        "retry_csv": str(output.relative_to(root)),
        "retry_count": len(rows),
        "item_ids": sorted(retry_ids),
    }


def command_cancel(args: argparse.Namespace, root: Path) -> dict:
    directory, manifest = load_run(root, args.phase, args.run_id)
    path = directory / "control.json"
    if path.is_file():
        existing = read_object(path)
        if existing.get("cancelled"):
            return {"cancelled": True, "changed": False, "control": existing}
    control = {
        "schema_version": "john.run-control.v1",
        "run_id": manifest["run_id"],
        "cancelled": True,
        "cancelled_at": now(),
        "reason": args.reason,
    }
    atomic_write_text(path, json.dumps(control, indent=2) + "\n")
    return {"cancelled": True, "changed": True, "control": control}


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__)
    sub = top.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--phase", required=True)
    create.add_argument("--run-id", required=True)
    create.add_argument("--work-csv", required=True)
    create.add_argument("--item-id-column", default="item_id")
    create.add_argument("--stage", default="work")
    create.add_argument("--provider", required=True)
    create.add_argument("--engine", required=True)
    create.add_argument("--worker-role", required=True)
    create.add_argument("--terminal-event", required=True)
    create.add_argument("--max-depth", type=int, default=1)
    create.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    create.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    create.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)

    record = sub.add_parser("record")
    for name in ("phase", "run-id", "item-id", "attempt-id", "provider", "engine", "worker"):
        record.add_argument(f"--{name}", required=True)
    record.add_argument(
        "--status", required=True, choices=("succeeded", "failed", "timed_out", "cancelled")
    )
    record.add_argument("--started-at")
    record.add_argument("--finished-at")
    record.add_argument("--event-file", action="append", default=[])
    record.add_argument("--error-json")

    for command in ("reconcile", "status", "retry-csv", "cancel"):
        current = sub.add_parser(command)
        current.add_argument("--phase", required=True)
        current.add_argument("--run-id", required=True)
        if command == "retry-csv":
            current.add_argument("--output")
        if command == "cancel":
            current.add_argument("--reason", default="cancelled by user")
    return top


def main() -> None:
    args = parser().parse_args()
    try:
        root = project_root()
        if args.command == "create":
            if min(args.max_depth, args.concurrency, args.timeout, args.max_attempts) < 1:
                raise ValueError("run policy values must be positive integers")
            result = command_create(args, root)
        elif args.command == "record":
            result = command_record(args, root)
        elif args.command == "reconcile":
            result = command_reconcile(args, root)
        elif args.command == "status":
            result = command_reconcile(args, root, write=False)
        elif args.command == "retry-csv":
            result = command_retry_csv(args, root)
        else:
            result = command_cancel(args, root)
        emit(result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        fail(str(exc))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
