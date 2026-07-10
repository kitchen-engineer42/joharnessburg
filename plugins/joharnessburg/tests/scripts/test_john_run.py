"""Tests for the durable, provider-neutral John run ledger."""

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR, run_script


SCRIPT = SCRIPTS_DIR / "john_run.py"


def run_ledger(root: Path, *args: str):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout) if result.stdout.strip() else None
    return result, payload


class TestJohnRun(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        rc, _, stderr = run_script("init_workspace.py", cwd=self.root)
        self.assertEqual(rc, 0, stderr)
        self.work = self.root / "input.csv"
        self.work.write_text("item_id,value\nitem-1,alpha\nitem-2,beta\n")

    def tearDown(self):
        self.temp.cleanup()

    def create(
        self, *extra: str, run_id: str = "run-1", engine: str = "native_wave"
    ):
        return run_ledger(
            self.root,
            "create",
            "--phase", "extract",
            "--run-id", run_id,
            "--work-csv", str(self.work),
            "--provider", "codex",
            "--engine", engine,
            "--worker-role", "extractor",
            "--terminal-event", "item_complete",
            *extra,
        )

    def record(self, item: str, attempt: str, event: Path | None = None, **kwargs):
        args = [
            "record", "--phase", "extract", "--run-id", "run-1",
            "--item-id", item, "--attempt-id", attempt,
            "--provider", "codex", "--engine", "native_wave",
            "--worker", "worker-1", "--status", kwargs.get("status", "succeeded"),
        ]
        if event:
            args.extend(["--event-file", str(event.relative_to(self.root))])
        if kwargs.get("error"):
            args.extend(["--error-json", json.dumps(kwargs["error"])])
        return run_ledger(self.root, *args)

    def event(self, item: str, *, valid: bool = True) -> Path:
        directory = self.root / ".john/events/extract" / item
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "terminal.json"
        body = {
            "event_type": "item_complete",
            "run_id": "run-1" if valid else "other-run",
            "item_id": item,
        }
        path.write_text(json.dumps(body))
        return path

    def test_create_is_transactional_immutable_and_uses_contract_defaults(self):
        result, payload = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["created"])
        manifest = payload["manifest"]
        self.assertEqual(
            manifest["policy"],
            {
                "max_depth": 1,
                "concurrency": 6,
                "per_worker_timeout_seconds": 1800,
                "max_attempts": 3,
            },
        )
        result, payload = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(payload["created"])
        result, payload = self.create(engine="spawn_agents_on_csv")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["success"])
        self.work.write_text("item_id,value\nitem-1,changed\n")
        result, payload = self.create()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["success"])

    def test_direct_wave_and_csv_engines_share_immutable_work_contract(self):
        _, direct = self.create(run_id="direct-run", engine="native_wave")
        _, csv_run = self.create(
            run_id="csv-run", engine="spawn_agents_on_csv"
        )
        for field in ("item_ids", "work_fields", "work_count", "work_checksum", "policy"):
            self.assertEqual(direct["manifest"][field], csv_run["manifest"][field])

    def test_completion_requires_matching_parseable_terminal_event(self):
        self.create()
        missing = self.root / ".john/events/extract/item-1/missing.json"
        result, _ = self.record("item-1", "attempt-1", missing)
        self.assertEqual(result.returncode, 0, result.stderr)
        result, payload = run_ledger(
            self.root, "reconcile", "--phase", "extract", "--run-id", "run-1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        first = payload["reconciliation"]["items"][0]
        self.assertEqual(first["status"], "invalid_artifacts")
        self.assertTrue(first["retryable"])

        valid = self.event("item-1", valid=False)
        self.record("item-1", "attempt-2", valid)
        _, payload = run_ledger(
            self.root, "reconcile", "--phase", "extract", "--run-id", "run-1"
        )
        self.assertIn("event run_id mismatch", " ".join(payload["reconciliation"]["items"][0]["reasons"]))

        valid.write_text("not-json")
        self.record("item-1", "attempt-3", valid)
        _, payload = run_ledger(
            self.root, "reconcile", "--phase", "extract", "--run-id", "run-1"
        )
        self.assertEqual(payload["reconciliation"]["items"][0]["status"], "invalid_artifacts")
        self.assertFalse(payload["reconciliation"]["items"][0]["retryable"])

    def test_success_retry_csv_cancel_and_reconcile_idempotency(self):
        self.create()
        event = self.event("item-1")
        first_result, first_payload = self.record("item-1", "attempt-1", event)
        self.assertEqual(first_result.returncode, 0, first_result.stderr)
        again_result, again_payload = self.record("item-1", "attempt-1", event)
        self.assertEqual(again_result.returncode, 0, again_result.stderr)
        self.assertFalse(again_payload["recorded"])

        result, payload = run_ledger(
            self.root, "reconcile", "--phase", "extract", "--run-id", "run-1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["reconciliation"]["counts"], {"completed": 1, "pending": 1})
        reconciliation = self.root / ".john/runs/extract/run-1/reconciliation.json"
        stable = reconciliation.read_bytes()
        run_ledger(self.root, "reconcile", "--phase", "extract", "--run-id", "run-1")
        self.assertEqual(stable, reconciliation.read_bytes())

        result, payload = run_ledger(
            self.root, "retry-csv", "--phase", "extract", "--run-id", "run-1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["item_ids"], ["item-2"])
        with (self.root / payload["retry_csv"]).open() as handle:
            self.assertEqual([row["item_id"] for row in csv.DictReader(handle)], ["item-2"])

        result, payload = run_ledger(
            self.root, "cancel", "--phase", "extract", "--run-id", "run-1",
            "--reason", "operator request",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["changed"])
        _, status = run_ledger(
            self.root, "status", "--phase", "extract", "--run-id", "run-1"
        )
        self.assertEqual(status["reconciliation"]["status"], "cancelled")

    def test_failed_attempts_are_structured_and_retry_limited(self):
        self.create("--max-attempts", "1")
        result, _ = self.record(
            "item-1", "attempt-1", status="timed_out", error={"code": "timeout", "message": "late"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        _, payload = run_ledger(
            self.root, "status", "--phase", "extract", "--run-id", "run-1"
        )
        item = payload["reconciliation"]["items"][0]
        self.assertEqual(item["status"], "timed_out")
        self.assertFalse(item["retryable"])
        self.assertEqual(item["error"]["code"], "timeout")

    def test_traversal_duplicates_and_event_symlinks_are_rejected(self):
        result, _ = run_ledger(
            self.root,
            "create", "--phase", "../escape", "--run-id", "run-1",
            "--work-csv", str(self.work), "--provider", "codex",
            "--engine", "native", "--worker-role", "worker",
            "--terminal-event", "done",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.root / ".john/escape").exists())

        self.create()
        event = self.event("item-1")
        self.record("item-1", "attempt-1", event)
        receipt = self.root / ".john/runs/extract/run-1/attempts/item-1/attempt-1.json"
        changed = json.loads(receipt.read_text())
        changed["worker"] = "different-worker"
        receipt.write_text(json.dumps(changed))
        result, payload = self.record("item-1", "attempt-1", event)
        self.assertEqual(result.returncode, 1)
        self.assertIn("different receipt", payload["error"])

        external = self.root / "external.json"
        external.write_text(event.read_text())
        event.unlink()
        os.symlink(external, event)
        _, payload = run_ledger(
            self.root, "status", "--phase", "extract", "--run-id", "run-1"
        )
        reasons = " ".join(payload["reconciliation"]["items"][0]["reasons"])
        self.assertIn("symlink", reasons)


if __name__ == "__main__":
    unittest.main()
