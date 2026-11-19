import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_data(monkeypatch, tmp_path):
    from app import paths
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path / "user-data")
    # create data directory as data_dir() would.
    (tmp_path / "user-data").mkdir()
    from app.ui import chat
    monkeypatch.setattr(chat, "data_dir", paths.data_dir)
