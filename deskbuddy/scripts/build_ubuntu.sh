#!/bin/bash
set -euo pipefail
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Ubuntu 包必须在 Ubuntu 24.04 上构建。" >&2
  exit 1
fi
ubuntu_release="$(. /etc/os-release; printf '%s:%s' "$ID" "$VERSION_ID")"
if [[ "$ubuntu_release" != "ubuntu:24.04" ]]; then
  echo "此构建目标为 Ubuntu 24.04，当前环境为 $ubuntu_release。" >&2
  exit 1
fi
cd "$(dirname "$0")/.."
project="$PWD"
architecture="$(dpkg --print-architecture)"
if [[ "$architecture" != "amd64" && "$architecture" != "arm64" ]]; then
  echo "支持的架构为 amd64 或 arm64。" >&2
  exit 1
fi
build_venv="${DESKBUDDY_BUILD_VENV:-$project/.venv-build-ubuntu}"
"${PYTHON_BIN:-python3}" -m venv "$build_venv"
"$build_venv/bin/python" -m pip install -r requirements-dev.txt
"$build_venv/bin/python" -m pytest -q
output="$project/../.artifacts/ubuntu/$architecture"
mkdir -p "$output"
"$build_venv/bin/python" -m PyInstaller --clean --noconfirm \
  --distpath "$output/dist" --workpath "$output/build" DeskBuddy.spec
"$build_venv/bin/python" scripts/smoke.py "$output/dist/DeskBuddy/DeskBuddy"
"$build_venv/bin/python" scripts/package_ubuntu.py \
  --bundle "$output/dist/DeskBuddy" --output "$output" --architecture "$architecture"
