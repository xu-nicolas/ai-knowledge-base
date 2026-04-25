#!/usr/bin/env bash
# Hook wrapper: reads JSON from stdin, extracts file_path from tool_input,
# and runs the Python validation script against that file.
#
# Claude Code command hooks receive JSON on stdin with fields like:
#   { "tool_name": "Write", "tool_input": { "file_path": "..." }, "cwd": "..." }

set -euo pipefail

# Read stdin into a variable (don't consume it before jq can parse)
INPUT=$(cat)

# Extract file_path from tool_input (supports both file_path and filePath)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tool_input = data.get('tool_input', {})
fp = tool_input.get('file_path') or tool_input.get('filePath', '')
print(fp, end='')
")

# Skip if no file path
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Only validate JSON files in knowledge/entries/
if [[ "$FILE_PATH" != *knowledge/entries/*.json ]]; then
    exit 0
fi

# Run the Python validation script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/validate_json.py" "$FILE_PATH"
