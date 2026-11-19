"""Keep bundled resources read-only and user data outside the app bundle."""
from pathlib import Path
import os
import sys


def resource_path(relative):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / relative


def data_dir():
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "DeskBuddy"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path(port=None):
    base = data_dir() if getattr(sys, "frozen", False) else resource_path(".")
    return base / (f"config_{port}.yaml" if port else "config.yaml")
