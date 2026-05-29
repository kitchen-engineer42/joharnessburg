#!/usr/bin/env python3
"""Compute per-rule confidence calibration from rule-testing + production-QC data.

Used by the [[confidence-system]] skill. Aggregates per-rule sample accuracy
from Phase 4 (.john/checkpoints/testing/<rule-id>/results.json) and Phase 7
(.john/checkpoints/qc/<batch-id>/sampling_review.json), computes
weighted_accuracy = (phase_4_acc * phase_4_n + phase_7_acc * phase_7_n) /
(phase_4_n + phase_7_n), and writes confidence_calibration.json.

Output schema:
  {
    "R042": {
      "phase_4_accuracy": 0.94,
      "phase_4_sample_count": 12,
      "phase_7_sampled_accuracy": 0.96,
      "phase_7_sample_count": 38,
      "weighted_accuracy": 0.955,
      "updated_at": "2026-05-27T10:00:00Z",
      "last_calibration_shift": 0.012
    },
    ...
  }

Logs deltas (rules whose weighted_accuracy shifted > 0.05) to stderr so the
user knows which rules are most volatile.

Usage:
  python3 confidence_calibrate.py \\
    --testing-results <project>/.john/checkpoints/testing/ \\
    --qc-results <project>/.john/checkpoints/qc/<latest-batch>/ \\
    [--prior <project>/confidence_calibration.json] \\
    --output <project>/confidence_calibration.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(msg, file=sys.stderr)


def load_testing_results(testing_dir: Path) -> dict:
    """Aggregate per-rule accuracy from .john/checkpoints/testing/<rule-id>/results.json."""
    per_rule = {}
    for rule_dir in sorted(testing_dir.glob("*/")):
        results_file = rule_dir / "results.json"
        if not results_file.exists():
            continue
        try:
            data = json.loads(results_file.read_text())
        except json.JSONDecodeError as e:
            err(f"failed to parse {results_file}: {e}")
            continue
        rule_id = data.get("rule_id") or rule_dir.name
        # Use the final per_sample list (after any iteration)
        per_sample = data.get("per_sample", [])
        if not per_sample:
            continue
        correct = sum(1 for s in per_sample if s.get("correct"))
        total = len(per_sample)
        per_rule[rule_id] = {
            "accuracy": correct / total if total else 0.0,
            "sample_count": total,
        }
    return per_rule


def load_qc_results(qc_dir: Path) -> dict:
    """Aggregate per-rule sampled accuracy from <qc-batch>/sampling_review.json."""
    review_file = qc_dir / "sampling_review.json"
    if not review_file.exists():
        info(f"  no sampling_review.json at {review_file} — skipping QC contribution")
        return {}
    try:
        data = json.loads(review_file.read_text())
    except json.JSONDecodeError as e:
        err(f"failed to parse {review_file}: {e}")
        return {}

    per_rule = {}
    # Expected schema: list of {rule_id, finding_id, judge_verdict, runtime_verdict, agreement: bool}
    findings = data.get("reviewed_findings", [])
    for f in findings:
        rid = f.get("rule_id")
        if not rid:
            continue
        entry = per_rule.setdefault(rid, {"agreements": 0, "total": 0})
        entry["total"] += 1
        if f.get("agreement"):
            entry["agreements"] += 1

    return {
        rid: {
            "accuracy": v["agreements"] / v["total"] if v["total"] else 0.0,
            "sample_count": v["total"],
        }
        for rid, v in per_rule.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testing-results", required=True, type=Path,
                        help="Path to .john/checkpoints/testing/")
    parser.add_argument("--qc-results", type=Path, default=None,
                        help="Path to .john/checkpoints/qc/<batch>/ (optional; skip QC contribution if not provided)")
    parser.add_argument("--prior", type=Path, default=None,
                        help="Path to existing confidence_calibration.json (for delta computation)")
    parser.add_argument("--output", required=True, type=Path,
                        help="Where to write the updated confidence_calibration.json")
    args = parser.parse_args()

    if not args.testing_results.exists():
        err(f"testing results dir doesn't exist: {args.testing_results}")
        return 1

    info(f"Loading Phase 4 testing results from {args.testing_results}")
    testing = load_testing_results(args.testing_results)
    info(f"  {len(testing)} rules with testing data")

    qc = {}
    if args.qc_results:
        if not args.qc_results.exists():
            err(f"QC results dir doesn't exist: {args.qc_results}")
            return 1
        info(f"Loading Phase 7 QC results from {args.qc_results}")
        qc = load_qc_results(args.qc_results)
        info(f"  {len(qc)} rules with QC data")

    prior = {}
    if args.prior and args.prior.exists():
        prior = json.loads(args.prior.read_text())
        info(f"Loaded prior calibration: {len(prior)} rules")

    now = datetime.now(timezone.utc).isoformat()
    output = {}
    all_rule_ids = set(testing.keys()) | set(qc.keys()) | set(prior.keys())

    shifts = []
    for rid in sorted(all_rule_ids):
        t = testing.get(rid, {})
        q = qc.get(rid, {})
        p = prior.get(rid, {})

        t_acc, t_n = t.get("accuracy", 0.0), t.get("sample_count", 0)
        q_acc, q_n = q.get("accuracy", 0.0), q.get("sample_count", 0)
        total_n = t_n + q_n
        if total_n > 0:
            weighted = (t_acc * t_n + q_acc * q_n) / total_n
        elif p.get("weighted_accuracy") is not None:
            weighted = p["weighted_accuracy"]
        else:
            weighted = 0.0

        prior_weighted = p.get("weighted_accuracy", weighted)
        shift = weighted - prior_weighted
        if abs(shift) > 0.05:
            shifts.append((rid, prior_weighted, weighted, shift))

        output[rid] = {
            "phase_4_accuracy": t_acc,
            "phase_4_sample_count": t_n,
            "phase_7_sampled_accuracy": q_acc,
            "phase_7_sample_count": q_n,
            "weighted_accuracy": round(weighted, 4),
            "updated_at": now,
            "last_calibration_shift": round(shift, 4),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    info(f"\nWrote {len(output)} rules to {args.output}")

    if shifts:
        info(f"\n{len(shifts)} rule(s) shifted > 0.05 — review:")
        for rid, before, after, delta in shifts:
            sign = "+" if delta > 0 else ""
            info(f"  {rid}: {before:.3f} → {after:.3f} ({sign}{delta:.3f})")
        info(f"\nLarge shifts may indicate calibration drift on production data;")
        info(f"consider re-running Phase 4 with samples drawn from the recent QC batch")
        info(f"for affected rules.")
    else:
        info(f"\nNo significant calibration shifts (> 0.05) detected.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
