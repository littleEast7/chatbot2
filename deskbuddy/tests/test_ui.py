import base64
import threading
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel
from app.config import load_config
from app.network import peer_target
from app.paths import resource_path
from app.scheduler import start_scheduler
from app.ui.assistant import AssistantWindow
from app.ui.chat import ChatWindow


@pytest.mark.parametrize(("value", "expected"), [("127.0.0.1", "127.0.0.1:9000"),
    ("localhost:9001", "localhost:9001"), ("::1", "[::1]:9000"), ("[::1]:9002", "[::1]:9002")])
def test_peer_address(value, expected):
    assert peer_target(value) == expected


@pytest.mark.parametrize("value", ["http://host", "host/path", "host:0", "host:99999", "user@host", "a b"])
def test_invalid_peer(value):
    with pytest.raises(ValueError):
        peer_target(value)


def test_threaded_reminder_and_timer(qapp, tmp_path):
    assistant = AssistantWindow(str(resource_path("assets/assistant.gif")), load_config(tmp_path / "missing"))
    worker = threading.Thread(target=assistant.remind, args=("<b>hello</b>",))
    worker.start()
    worker.join()
    qapp.processEvents()
    assert assistant.bubble.text() == "<b>hello</b>"
    assert assistant.bubble.textFormat() == Qt.PlainText
    assert assistant.hide_timer.isSingleShot()
    assert assistant.movie.isValid()
    assistant.close()


def test_http_failure_reported(qapp, tmp_path, monkeypatch):
    chat = ChatWindow(load_config(tmp_path / "missing"), tmp_path / "config.yaml")
    response = Mock()
    response.raise_for_status.side_effect = RuntimeError("HTTP 500")
    monkeypatch.setattr("app.ui.chat.requests.post", Mock(return_value=response))
    chat._send_http("127.0.0.1", "hello")
    qapp.processEvents()
    assert any("发送失败" in label.text() for label in chat.findChildren(QLabel))
    chat.deleteLater()


def test_avatar_queued_and_path_safe(qapp, tmp_path):
    chat = ChatWindow(load_config(tmp_path / "missing"), tmp_path / "config.yaml")
    from PySide6.QtGui import QImage
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    image = QImage(8, 8, QImage.Format_RGB32)
    image.fill(Qt.red)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    payload = base64.b64encode(bytes(data)).decode()
    worker = threading.Thread(target=chat.on_handshake_received,
                              args=("127.0.0.1", 9001, payload, "../../escape"))
    worker.start()
    worker.join()
    assert chat.friend_avatar_path is None
    qapp.processEvents()
    assert str(tmp_path / "user-data" / "cache") in chat.friend_avatar_path
    assert chat.ip_input.text() == "127.0.0.1:9001"
    chat.connected_avatar.click()
    assert not chat.right_container.isHidden()
    chat.add_message_item("<b>literal</b>", True)
    assert any(label.text() == "<b>literal</b>" and label.textFormat() == Qt.PlainText
               for label in chat.findChildren(QLabel))
    chat.deleteLater()


def test_scheduler(qapp, tmp_path):
    config = load_config(tmp_path / "missing")
    assistant = Mock()
    scheduler = start_scheduler(config, assistant)
    try:
        assert len(scheduler.get_jobs()) == 1
        assert scheduler.get_jobs()[0].args == (config["reminders"][0]["text"],)
    finally:
        scheduler.shutdown()


@pytest.mark.parametrize("body", [b'[]', b'{"status":"error"}', b'not-json'])
def test_invalid_peer_response(qapp, tmp_path, monkeypatch, body):
    chat = ChatWindow(load_config(tmp_path / "missing"), tmp_path / "config.yaml")
    response = Mock()
    response.iter_content.return_value = [body]
    monkeypatch.setattr("app.ui.chat.requests.post", Mock(return_value=response))
    chat._send_http("127.0.0.1", "hello")
    assert any("发送失败" in label.text() for label in chat.findChildren(QLabel))
    response.close.assert_called_once()
    chat.deleteLater()


def test_peer_response_size_limit(qapp, tmp_path, monkeypatch):
    chat = ChatWindow(load_config(tmp_path / "missing"), tmp_path / "config.yaml")
    response = Mock()
    response.iter_content.return_value = [b"x" * 65536] * 49
    monkeypatch.setattr("app.ui.chat.requests.post", Mock(return_value=response))
    with pytest.raises(ValueError, match="响应过大"):
        chat._post_peer("http://127.0.0.1/remind", {})
    response.close.assert_called_once()
    chat.deleteLater()


def test_busy_worker_preserves_input(qapp, tmp_path):
    chat = ChatWindow(load_config(tmp_path / "missing"), tmp_path / "config.yaml")
    chat.ip_input.setText("127.0.0.1")
    chat.msg_input.setText("pending")
    for _ in range(4):
        assert chat._network_slots.acquire(blocking=False)
    chat.send_message()
    assert chat.msg_input.text() == "pending"
    chat.deleteLater()
