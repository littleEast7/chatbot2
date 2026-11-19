#!/bin/bash
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS .app 必须在 macOS 上构建。" >&2
  exit 1
fi
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m venv .venv-build
.venv-build/bin/python -m pip install -r requirements-dev.txt
.venv-build/bin/python -m pytest -q
.venv-build/bin/python -m PyInstaller --clean --noconfirm DeskBuddy.spec
# Exercise the bundled executable from a different working directory.
bundle="$PWD/dist/DeskBuddy.app"
.venv-build/bin/python scripts/smoke.py "$bundle/Contents/MacOS/DeskBuddy"
codesign --verify --deep --strict "$bundle"
archive="dist/DeskBuddy-macOS-$(uname -m).zip"
ditto -c -k --sequesterRsrc --keepParent "$bundle" "$archive"
echo "构建完成：$archive"
