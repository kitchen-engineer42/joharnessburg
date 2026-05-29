#!/usr/bin/env python3
"""Scaffold the produced verification app's release bundle into a John project.

Used by the [[packaging]] skill in Phase 8 of a doc-verification project. Copies
the templated runtime (kc_runtime/, run.py, render_dashboard.py, dashboard
templates) from the plugin's release_bundle_assets/ into <project>/<target>/,
substituting project-specific values (severity vocab, project name, etc.).

After scaffolding, layer-2 Claude customizes the dashboard fields per project
(see the dashboard-reporting skill).

Usage:
  python3 scaffold_release_bundle.py \\
    --project <project-root> \\
    --target release/v1 \\
    --catalog <project>/.john/knowledge/catalog.json \\
    --glossary <project>/.john/knowledge/glossary.json \\
    --calibration <project>/confidence_calibration.json \\
    --workflows <project>/workflows \\
    --severity-vocab critical high medium low advisory \\
    [--pdf-review-dashboard]
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR / "release_bundle_assets"


def err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(msg, file=sys.stderr)


def render_template(template_text: str, substitutions: dict) -> str:
    """Lightweight string-substitution renderer.

    Templates use {{ key }} placeholders (Jinja2-style but no logic).
    The HTML dashboard itself is rendered at runtime by render_dashboard.py
    (via Jinja2 if installed, or a small built-in fallback if not).
    """
    rendered = template_text
    for key, value in substitutions.items():
        rendered = rendered.replace("{{ " + key + " }}", str(value))
    return rendered


def copy_with_substitution(src: Path, dst: Path, substitutions: dict) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix == ".tmpl":
        text = src.read_text()
        rendered = render_template(text, substitutions)
        # Drop the .tmpl suffix
        final_dst = dst.with_suffix("") if dst.suffix == ".tmpl" else dst
        final_dst.write_text(rendered)
        info(f"  rendered: {final_dst.relative_to(dst.parent.parent.parent) if dst.parent.parent.parent in final_dst.parents else final_dst}")
    else:
        shutil.copy2(src, dst)
        info(f"  copied:   {dst.relative_to(dst.parent.parent.parent) if dst.parent.parent.parent in dst.parents else dst}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path,
                        help="Project root (the .john/ workspace)")
    parser.add_argument("--target", default="release/v1", type=str,
                        help="Where to scaffold the bundle, relative to --project")
    parser.add_argument("--catalog", required=True, type=Path,
                        help="Path to the rule catalog JSON")
    parser.add_argument("--glossary", required=True, type=Path,
                        help="Path to the glossary JSON")
    parser.add_argument("--calibration", required=True, type=Path,
                        help="Path to confidence_calibration.json")
    parser.add_argument("--workflows", required=True, type=Path,
                        help="Path to <project>/workflows/ (distilled workflows dir)")
    parser.add_argument("--severity-vocab", nargs="+", required=True,
                        help="Project's severity values (space-separated, in priority order)")
    parser.add_argument("--pdf-review-dashboard", action="store_true",
                        help="Also scaffold the optional PDF review dashboard")
    args = parser.parse_args()

    project = args.project.resolve()
    target_dir = (project / args.target).resolve()

    if not project.exists():
        err(f"project dir doesn't exist: {project}")
        return 1
    if not ASSETS_DIR.exists():
        err(f"release_bundle_assets/ not found at: {ASSETS_DIR}")
        err("Is the plugin install intact?")
        return 1
    if target_dir.exists() and any(target_dir.iterdir()):
        err(f"target already exists and is non-empty: {target_dir}")
        err("Refusing to overwrite. Delete it or use a different --target.")
        return 1

    # Validate inputs
    for label, path in [("catalog", args.catalog), ("glossary", args.glossary),
                        ("calibration", args.calibration)]:
        if not path.exists():
            err(f"{label} doesn't exist: {path}")
            return 1
    if not args.workflows.exists() or not args.workflows.is_dir():
        err(f"workflows dir doesn't exist: {args.workflows}")
        return 1

    catalog = json.loads(args.catalog.read_text())
    rule_ids = sorted(catalog.get("rules", {}).keys()) if isinstance(catalog.get("rules"), dict) \
        else [r.get("id") for r in catalog if isinstance(catalog, list)]

    # Build substitutions
    substitutions = {
        "PROJECT_NAME": project.name,
        "BUILD_DATE": datetime.now(timezone.utc).isoformat(),
        "RULE_COUNT": str(len(rule_ids)),
        "SEVERITY_VOCAB_PYLIST": json.dumps(args.severity_vocab),
        "SEVERITY_VOCAB_DISPLAY": " / ".join(args.severity_vocab),
        "PDF_REVIEW_ENABLED": str(args.pdf_review_dashboard).lower(),
    }

    info(f"Scaffolding release bundle: {target_dir}")
    info(f"  project: {project.name}")
    info(f"  rules:   {len(rule_ids)}")
    info(f"  severity vocab: {substitutions['SEVERITY_VOCAB_DISPLAY']}")

    target_dir.mkdir(parents=True, exist_ok=True)

    # Core runtime files
    core_files = [
        ("run.py.tmpl", "run.py"),
        ("render_dashboard.py.tmpl", "render_dashboard.py"),
        ("serve.sh.tmpl", "serve.sh"),
        ("README.md.tmpl", "README.md"),
        ("kc_runtime/__init__.py", "kc_runtime/__init__.py"),
        ("kc_runtime/confidence.py.tmpl", "kc_runtime/confidence.py"),
        ("kc_runtime/dashboard.py.tmpl", "kc_runtime/dashboard.py"),
    ]
    if args.pdf_review_dashboard:
        core_files.append(("kc_runtime/pdf_review.py.tmpl",
                           "kc_runtime/pdf_review.py"))

    for src_rel, dst_rel in core_files:
        src = ASSETS_DIR / src_rel
        dst = target_dir / dst_rel
        if not src.exists():
            err(f"asset missing in plugin install: {src_rel}")
            return 1
        copy_with_substitution(src, dst, substitutions)

    # serve.sh needs to be executable
    serve_sh = target_dir / "serve.sh"
    if serve_sh.exists():
        serve_sh.chmod(0o755)

    # Copy data snapshots
    snapshot_targets = {
        args.catalog: target_dir / "catalog.json",
        args.glossary: target_dir / "glossary.json",
        args.calibration: target_dir / "confidence_calibration.json",
    }
    for src, dst in snapshot_targets.items():
        shutil.copy2(src, dst)
        info(f"  snapshot: {dst.relative_to(target_dir.parent)}")

    # Copy workflows
    workflows_dst = target_dir / "workflows"
    if workflows_dst.exists():
        shutil.rmtree(workflows_dst)
    shutil.copytree(args.workflows, workflows_dst)
    info(f"  workflows: {sum(1 for _ in workflows_dst.rglob('workflow.py'))} found")

    # Create fixtures/ + workflows/.gitkeep
    (target_dir / "fixtures").mkdir(exist_ok=True)
    (target_dir / "fixtures" / ".gitkeep").touch()

    # Stub models.json — user fills in
    models_json = target_dir / "models.json"
    if not models_json.exists():
        models_json.write_text(json.dumps({
            "TIER1": "<sota-model-id>",
            "TIER2": "<medium-model-id>",
            "TIER3": "<cheap-model-id>",
            "TIER4": "<cheapest-model-id>",
            "_comment": "Fill in with actual provider/model IDs before deploying.",
        }, indent=2) + "\n")
        info(f"  stub:     models.json (fill in before deploying)")

    # Write manifest.json
    manifest = {
        "project_name": project.name,
        "bundle_version": "v1",
        "build_date": substitutions["BUILD_DATE"],
        "rule_count": len(rule_ids),
        "rule_ids": rule_ids,
        "severity_vocab": args.severity_vocab,
        "pdf_review_enabled": args.pdf_review_dashboard,
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    info(f"  manifest: manifest.json")

    info(f"\nRelease bundle scaffolded at: {target_dir}")
    info(f"\nNext steps:")
    info(f"  1. Customize kc_runtime/dashboard.py SEVERITY_COLORS for the project's domain.")
    info(f"  2. Fill in models.json with actual TIER1-TIER4 model IDs.")
    info(f"  3. Optionally add fixtures/ samples for smoke testing.")
    info(f"  4. Smoke-test: python3 {target_dir / 'run.py'} <a-sample-doc>")
    info(f"  5. Translate dashboard labels to the project's declared language.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
