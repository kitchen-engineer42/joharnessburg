"""Shared test helpers — subprocess wrapper around the plugin's scripts."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def run_script(
    script_name: str,
    *args,
    cwd: Optional[Path] = None,
    env_override: Optional[dict] = None,
):
    """Run a toolkit script as a subprocess.

    Args:
        script_name: filename under scripts/, e.g. "init_workspace.py".
        *args: CLI args passed after the script name.
        cwd: working dir for the subprocess (defaults to inherit).
        env_override: extra env vars to add to (or override in) the subprocess
            environment. The base env is os.environ. Pass None for default env.

    Returns (returncode, stdout_json, stderr_text). stdout_json is the parsed
    JSON object if stdout is parseable, else None.
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name)] + list(args)
    env = None
    if env_override:
        env = os.environ.copy()
        env.update({k: str(v) for k, v in env_override.items()})
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=env,
    )
    try:
        stdout_json = json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError:
        stdout_json = None
    return result.returncode, stdout_json, result.stderr
