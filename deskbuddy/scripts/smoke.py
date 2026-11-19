"""Run an app binary with a clean profile and an unrelated working directory."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile


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
        subprocess.run(command + ["--config", str(config), "--smoke-test"],
                       cwd=root, env=environment, check=True, timeout=30)
    print("Smoke test passed: startup, GIF, handshake, reminder, GUI signals and shutdown")


if __name__ == "__main__":
    main()
