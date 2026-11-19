from pathlib import Path
import sys

import pytest
from app.config import load_config, save_config
from app import paths


def test_missing_and_partial_config(tmp_path):
    path = tmp_path / "config.yaml"
    assert load_config(path)["server"]["port"] == 9000
    path.write_text("server:\n  port: 9001\n", encoding="utf-8")
    config = load_config(path)
    assert config["server"] == {"host": "0.0.0.0", "port": 9001}
    save_config(config, path)
    assert load_config(path) == config


@pytest.mark.parametrize("content", ["[]", "server: null", "server: {port: 0}",
    "server: {port: true}", "reminders: null", "ui: {gif: null}",
    "reminders: [{type: interval, minutes: .nan, text: hello}]",
    "reminders: [{type: interval, minutes: -1, text: hello}]",
    "reminders: [{type: interval, minutes: 1, text: 123}]", "ui: {gif: {max_width: 0}}",
    "my_avatar: []", "a: [", "server: {token: []}",
    "server: {token: 中文}", "server: {token: 'contains space'}"])
def test_invalid_config(tmp_path, content):
    path = tmp_path / "config.yaml"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_config(path)


def test_frozen_paths_do_not_depend_on_cwd(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.chdir(tmp_path)
    assert paths.config_path().parent == tmp_path / "user-data"
    assert paths.resource_path("assets/assistant.gif") == tmp_path / "bundle/assets/assistant.gif"


def test_atomic_save_preserves_existing_file_on_error(tmp_path):
    path = tmp_path / "config.yaml"
    save_config({"target_ip": "old"}, path)
    with pytest.raises(Exception):
        save_config({"bad": object()}, path)
    assert load_config(path)["target_ip"] == "old"
    assert list(tmp_path.glob("tmp*")) == []
