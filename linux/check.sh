#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uv sync --project linux --python "${MOUTHKEYS_PYTHON:-3.13}" --extra gui --locked
uv run --project linux ruff check linux
uv run --project linux ruff format --check linux
QT_QPA_PLATFORM=offscreen uv run --project linux pytest linux/tests
uv build linux
