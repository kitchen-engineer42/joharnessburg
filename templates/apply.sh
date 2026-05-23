#!/bin/bash
# Universal apply wrapper for John templates.
#
# Each template ships its own apply.sh which is a symlink (or copy) of this file.
# Running ./apply.sh from inside a template directory builds the merged plugin
# at ~/.claude/plugins/joharnessburg-applied/<template-name>/.
#
# After it runs, the user launches:
#   claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<template-name>/

set -euo pipefail

TEMPLATE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve the John plugin install — apply_template.py auto-discovers via
# installed_plugins.json, but the script itself lives inside that install,
# so prefer to call it from wherever it's already located.
APPLY_SCRIPT="${CLAUDE_PLUGIN_ROOT:-}/scripts/apply_template.py"
if [ ! -f "$APPLY_SCRIPT" ]; then
    # Fall back to inferring CLAUDE_PLUGIN_ROOT from installed_plugins.json.
    # This is needed when apply.sh is run from a template dir outside the plugin.
    INSTALLED_PLUGINS="${HOME}/.claude/plugins/installed_plugins.json"
    if [ -f "$INSTALLED_PLUGINS" ]; then
        APPLY_SCRIPT_FALLBACK="$(python3 -c '
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
data = json.loads(p.read_text())
for k, entries in data.get("plugins", {}).items():
    if k.startswith("joharnessburg") and entries:
        path = entries[0].get("installPath")
        if path:
            print(path + "/scripts/apply_template.py")
            break
' "$INSTALLED_PLUGINS" 2>/dev/null)"
        if [ -n "$APPLY_SCRIPT_FALLBACK" ] && [ -f "$APPLY_SCRIPT_FALLBACK" ]; then
            APPLY_SCRIPT="$APPLY_SCRIPT_FALLBACK"
        fi
    fi
fi

if [ ! -f "$APPLY_SCRIPT" ]; then
    echo "Error: cannot locate apply_template.py. Is joharnessburg installed?" >&2
    echo "Tried: \$CLAUDE_PLUGIN_ROOT/scripts/apply_template.py and installed_plugins.json fallback." >&2
    exit 1
fi

exec python3 "$APPLY_SCRIPT" --template-root "$TEMPLATE_ROOT" "$@"
