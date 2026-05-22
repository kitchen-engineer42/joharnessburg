"""Shared test helpers — subprocess wrapper around the M2 toolkit scripts."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def run_script(script_name: str, *args, cwd: Optional[Path] = None):
    """Run a toolkit script as a subprocess.

    Returns (returncode, stdout_json, stderr_text). stdout_json is the parsed
    JSON object if stdout is parseable, else None.
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name)] + list(args)
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    try:
        stdout_json = json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError:
        stdout_json = None
    return result.returncode, stdout_json, result.stderr
