from unittest.mock import Mock
import base64
import socket

import pytest
import requests
from app.server import create_app, start_server


@pytest.mark.parametrize("payload", [[], None, "text", {"text": []}, {"text": ""},
    {"text": "x" * 10001}, {"text": "hello", "port": "9000"}, {"port": True}, {"port": 65536}])
def test_invalid_messages(payload):
    assistant = Mock()
    client = create_app(assistant).test_client()
    response = client.post("/remind", json=payload)
    assert response.status_code == 400
    assistant.remind.assert_not_called()


def test_success_and_auth():
    assistant, chat = Mock(), Mock()
    client = create_app(assistant, chat, "shared-secret").test_client()
    assert client.post("/remind", json={"text": "hi"}).status_code == 401
    response = client.post("/remind", json={"text": "hello", "port": 9001},
                           headers={"Authorization": "Bearer shared-secret"})
    assert response.status_code == 200
    assistant.remind.assert_called_once_with("hello")
    chat.on_message_received.assert_called_once_with("hello", "127.0.0.1", 9001)


@pytest.mark.parametrize("payload", [{"avatar": []}, {"avatar": "!!!"}, {"user_id": []},
    {"avatar": base64.b64encode(b"x" * (2 * 1024 * 1024 + 1)).decode()}])
def test_invalid_handshake(payload):
    assert create_app().test_client().post("/handshake", json=payload).status_code == 400


def test_request_size_limit():
    response = create_app().test_client().post("/handshake", data=b"x" * (3 * 1024 * 1024 + 1),
                                              content_type="application/json")
    assert response.status_code == 413


def test_server_shutdown_releases_port():
    # Port 0 is used only here to have the OS allocate an available test port.
    server = start_server({"server": {"host": "127.0.0.1", "port": 0}}, Mock())
    port = server.server.server_port
    session = requests.Session()
    session.trust_env = False
    try:
        assert session.post(f"http://127.0.0.1:{port}/remind", json={"text": "hi"}, timeout=3).ok
    finally:
        session.close()
        server.shutdown()
    assert not server.thread.is_alive()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


def test_port_conflict_is_reported():
    server = start_server({"server": {"host": "127.0.0.1", "port": 0}}, Mock())
    try:
        with pytest.raises(OSError, match="端口"):
            start_server({"server": {"host": "127.0.0.1", "port": server.server.server_port}}, Mock())
    finally:
        server.shutdown()
