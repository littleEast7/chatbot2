"""Run an app binary with a clean profile and an unrelated working directory."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def main():
    command = [os.path.abspath(arg) for arg in sys.argv[1:]]
    if not command:
        raise SystemExit("Usage: python scripts/smoke.py /path/to/executable [main.py]")
    with tempfile.TemporaryDirectory(prefix="deskbuddy-smoke-") as temporary:
        root = Path(temporary)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        config = root / "config.yaml"
        config.write_text(f"server:\n  host: 127.0.0.1\n  port: {port}\nreminders: []\n", encoding="utf-8")
        environment = dict(os.environ)
        # Linux verification uses the offscreen plugin; macOS uses native Cocoa.
        if sys.platform.startswith("linux"):
            environment.setdefault("QT_QPA_PLATFORM", "offscreen")
        stacks = root / "startup-stacks.log"
        environment["DESKBUDDY_SMOKE_STACKS"] = str(stacks)
        # macOS may scan a newly signed bundle on first launch. Keep a finite
        # allowance and collect a stack trace at 30s to distinguish slow startup
        # from an application deadlock.
        timeout = 90 if sys.platform == "darwin" else 30
        started = time.monotonic()
        try:
            subprocess.run(command + ["--config", str(config), "--smoke-test"],
                           cwd=root, env=environment, check=True, timeout=timeout)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if stacks.exists():
                print(stacks.read_text(errors="replace"), file=sys.stderr)
            if sys.platform == "darwin":
                log = Path.home() / "Library/Application Support/DeskBuddy/deskbuddy.log"
                if log.exists():
                    print(log.read_text(errors="replace")[-20000:], file=sys.stderr)
            raise
        print(f"Bundled startup and checks completed in {time.monotonic() - started:.1f}s")
    print("Smoke test passed: startup, GIF, handshake, reminder, GUI signals and shutdown")


if __name__ == "__main__":
    main()
