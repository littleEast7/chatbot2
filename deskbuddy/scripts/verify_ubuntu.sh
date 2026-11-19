#!/bin/bash
# Run inside a disposable clean Ubuntu 24.04 container, never the host system.
set -euo pipefail
if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Usage: bash verify_ubuntu.sh /artifacts/deskbuddy_VERSION_ARCH.deb" >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends "$1" xvfb xauth fonts-noto-cjk
if command -v python3 >/dev/null 2>&1; then
  echo "Clean runtime test must not have a system Python interpreter." >&2
  exit 1
fi
runtime_test_dir="$(mktemp -d)"
trap 'rm -rf "$runtime_test_dir"' EXIT
export XDG_DATA_HOME="$runtime_test_dir/data"
# The fresh container has no services on this dedicated test port.
printf 'server:\n  host: 127.0.0.1\n  port: 19090\nreminders: []\n' > "$runtime_test_dir/config.yaml"
cd "$runtime_test_dir"
if ! timeout 30s xvfb-run -a env QT_QPA_PLATFORM=xcb \
  /usr/bin/deskbuddy --config "$runtime_test_dir/config.yaml" --smoke-test; then
  if [[ -f "$XDG_DATA_HOME/DeskBuddy/deskbuddy.log" ]]; then
    cat "$XDG_DATA_HOME/DeskBuddy/deskbuddy.log" >&2
  fi
  exit 1
fi
if ! grep -q 'SMOKE_TEST_OK' "$XDG_DATA_HOME/DeskBuddy/deskbuddy.log"; then
  cat "$XDG_DATA_HOME/DeskBuddy/deskbuddy.log" >&2
  exit 1
fi
printf 'Verified: Ubuntu 24.04 package installed and GUI/HTTP checks passed without system Python.\n'
