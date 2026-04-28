#!/usr/bin/env bash
# motion-detective CLI shortcut — runs main.py via uv from the repo root.
set -euo pipefail
cd "$(dirname "$0")"
exec uv run python main.py "$@"
