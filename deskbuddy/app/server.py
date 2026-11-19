"""Bounded HTTP input and a server with an explicit shutdown lifecycle."""
import base64
import binascii
import hmac
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.serving import make_server

from app.config import valid_port

MAX_AVATAR_BYTES = 2 * 1024 * 1024


def create_app(assistant=None, chat_window=None, token=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024

    @app.before_request
    def authenticate():
        if token and not hmac.compare_digest(request.headers.get("Authorization", "").encode("utf-8"),
                                             f"Bearer {token}".encode("utf-8")):
            return jsonify(error="Unauthorized"), 401

    def payload():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        if "port" in data and not valid_port(data["port"]):
            raise ValueError("port must be an integer between 1 and 65535")
        return data

    @app.errorhandler(ValueError)
    def bad_request(error):
        return jsonify(error=str(error)), 400

    @app.post("/remind")
    def remind():
        data = payload()
        text = data.get("text", "提醒你一下～")
        if not isinstance(text, str) or not text.strip() or len(text) > 10000:
            raise ValueError("text must contain 1–10000 characters")
        if assistant is not None:
            assistant.remind(text)
        if chat_window is not None:
            chat_window.on_message_received(text, request.remote_addr, data.get("port"))
        return jsonify(status="ok")

    @app.post("/handshake")
    def handshake():
        data = payload()
        avatar = data.get("avatar")
        user_id = data.get("user_id")
        if user_id is not None and (not isinstance(user_id, str) or len(user_id) > 128):
            raise ValueError("user_id must be a string of at most 128 characters")
        if avatar is not None:
            if not isinstance(avatar, str):
                raise ValueError("avatar must be base64 text")
            try:
                decoded = base64.b64decode(avatar, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Invalid base64 avatar") from exc
            if len(decoded) > MAX_AVATAR_BYTES:
                raise ValueError("Avatar exceeds 2 MiB")
        my_avatar = None
        my_id = None
        if chat_window is not None:
            chat_window.on_handshake_received(request.remote_addr, data.get("port"), avatar, user_id)
            my_id = chat_window.config.get("user_id")
            path = chat_window.current_avatar_path
            if path:
                try:
                    with Path(path).open("rb") as stream:
                        content = stream.read(MAX_AVATAR_BYTES + 1)
                    if len(content) <= MAX_AVATAR_BYTES:
                        my_avatar = base64.b64encode(content).decode("ascii")
                except OSError:
                    pass
        return jsonify(status="ok", message="Handshake accepted", user_id=my_id, avatar=my_avatar)

    return app


class HttpServer:
    def __init__(self, config, assistant, chat_window=None):
        application = create_app(assistant, chat_window, config["server"].get("token"))
        # Bind synchronously so a port conflict is reported in the startup UI.
        try:
            self.server = make_server(config["server"]["host"], config["server"]["port"], application, threaded=True)
        except SystemExit as exc:
            raise OSError("HTTP 端口无法绑定，请检查端口占用和监听地址") from exc
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="DeskBuddy-HTTP")

    def start(self):
        self.thread.start()
        return self

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


def start_server(config, assistant, chat_window=None):
    return HttpServer(config, assistant, chat_window).start()
