"""Validated configuration and atomic persistence."""
import copy
import math
import os
from pathlib import Path
import tempfile

import yaml

DEFAULT_CONFIG = {
    "server": {"host": "0.0.0.0", "port": 9000},
    "ui": {"bubble": {"font_size": 18, "max_width": 350, "padding": 12},
           "gif": {"max_height": 350, "max_width": 350}},
    "reminders": [{"type": "interval", "minutes": 30, "text": "该起来活动一下啦 🧘"}],
    "target_ip": "", "my_avatar": "",
}


def _merge(defaults, values):
    result = copy.deepcopy(defaults)
    for key, value in values.items():
        if key in result and isinstance(result[key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"配置 {key} 必须是对象")
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def valid_port(value):
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 65535


def load_config(path="config.yaml"):
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as stream:
            values = yaml.safe_load(stream)
    except FileNotFoundError:
        values = {}
    except yaml.YAMLError as exc:
        raise ValueError(f"配置 YAML 格式错误: {exc}") from exc
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise ValueError("配置文件顶层必须是对象")
    config = _merge(DEFAULT_CONFIG, values)
    server = config["server"]
    if not valid_port(server["port"]) or not isinstance(server["host"], str) or not server["host"].strip():
        raise ValueError("server.host 必须是非空字符串，server.port 必须在 1–65535 内")
    token = server.get("token")
    if token is not None and (not isinstance(token, str) or len(token) > 512
                              or any(ord(char) < 33 or ord(char) > 126 for char in token)):
        raise ValueError("server.token 必须是最多 512 字符、不含空格的 ASCII 字符串")
    if "user_id" in config and (not isinstance(config["user_id"], str) or not config["user_id"] or len(config["user_id"]) > 128):
        raise ValueError("user_id 必须是 1–128 字符的字符串")
    if not isinstance(config["reminders"], list):
        raise ValueError("reminders 必须是列表")
    for reminder in config["reminders"]:
        if not isinstance(reminder, dict) or reminder.get("type") != "interval":
            raise ValueError("提醒必须包含 type: interval")
        minutes = reminder.get("minutes")
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not math.isfinite(minutes) or minutes <= 0:
            raise ValueError("提醒间隔 minutes 必须是有限正数")
        if not isinstance(reminder.get("text"), str) or not reminder["text"].strip():
            raise ValueError("提醒 text 必须是非空字符串")
    for group in ("bubble", "gif"):
        for key, value in config["ui"][group].items():
            if key in DEFAULT_CONFIG["ui"][group] and (isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 4096):
                raise ValueError(f"ui.{group}.{key} 必须是 1–4096 的整数")
    for key in ("target_ip", "my_avatar"):
        if not isinstance(config[key], str):
            raise ValueError(f"{key} 必须是字符串")
    if config["my_avatar"] and not Path(config["my_avatar"]).is_absolute():
        config["my_avatar"] = str((path.parent / config["my_avatar"]).resolve())
    return config


def save_config(config, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = stream.name
            yaml.safe_dump(config, stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
