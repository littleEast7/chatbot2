"""DeskBuddy desktop entry point (source and frozen application)."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import uuid

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import load_config, save_config, valid_port
from app.paths import config_path, data_dir, resource_path
from app.scheduler import start_scheduler
from app.server import start_server
from app.ui.assistant import AssistantWindow
from app.ui.chat import ChatWindow


def main():
    parser = argparse.ArgumentParser(description="DeskBuddy")
    parser.add_argument("--port", type=int, help="Server port (1–65535)")
    parser.add_argument("--config", type=Path, help="Explicit configuration file")
    parser.add_argument("--smoke-test", action="store_true", help="Run startup, HTTP and GUI checks, then exit")
    args, _ = parser.parse_known_args()
    if args.port is not None and not valid_port(args.port):
        parser.error("--port must be between 1 and 65535")

    if sys.platform.startswith("linux"):
        modifiers = os.environ.get("XMODIFIERS", "")
        for method in ("fcitx", "ibus"):
            if f"@im={method}" in modifiers:
                os.environ.setdefault("QT_IM_MODULE", method)

    app = QApplication(sys.argv)
    app.setApplicationName("DeskBuddy")
    app.setOrganizationName("DeskBuddy")
    scheduler = server = None
    try:
        log_path = data_dir() / "deskbuddy.log"
        logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")])
        path = args.config.resolve() if args.config else config_path(args.port)
        # A new port profile inherits settings, but receives its own peer identity.
        base = config_path()
        if args.port and not args.config and not path.exists() and base.exists():
            config = load_config(base)
            config.pop("user_id", None)
        else:
            config = load_config(path)
        if args.port is not None:
            config["server"]["port"] = args.port
        config.setdefault("user_id", uuid.uuid4().hex)
        save_config(config, path)

        assistant = AssistantWindow(str(resource_path("assets/assistant.gif")), config)
        if not assistant.movie.isValid():
            raise ValueError("助手 GIF 资源缺失或损坏")
        geometry = app.primaryScreen().availableGeometry()
        width = min(geometry.width(), config["ui"]["gif"]["max_width"] + 30)
        height = min(geometry.height(), config["ui"]["gif"]["max_height"] + 160)
        assistant.resize(width, height)
        position = config.get("window", {})
        if not isinstance(position, dict):
            raise ValueError("window 必须是对象")
        x = position.get("x", geometry.right() - width - 20)
        y = position.get("y", geometry.bottom() - height - 20)
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("window.x 和 window.y 必须是整数")
        assistant.move(max(geometry.left(), min(x, geometry.right() - width + 1)),
                       max(geometry.top(), min(y, geometry.bottom() - height + 1)))
        chat = ChatWindow(config, config_path=path)
        chat.setWindowTitle(f"DeskBuddy — {config['server']['port']}")
        # Only display windows after every service has started successfully.
        server = start_server(config, assistant, chat)
        scheduler = start_scheduler(config, assistant)
        chat.show()
        assistant.start_greeting()

        if args.smoke_test:
            def smoke_test():
                try:
                    import requests
                    from app.network import sender_address
                    port = config["server"]["port"]
                    host = config["server"]["host"]
                    if host in ("0.0.0.0", "::"):
                        host = "127.0.0.1" if host == "0.0.0.0" else "::1"
                    endpoint = "http://" + sender_address(host, port)
                    token = config["server"].get("token")
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    with requests.Session() as session:
                        session.trust_env = False
                        for route, payload in (("handshake", {"port": port}),
                                               ("remind", {"text": "DeskBuddy smoke test", "port": port})):
                            response = session.post(f"{endpoint}/{route}", json=payload,
                                                    headers=headers, timeout=3)
                            response.raise_for_status()
                            assert response.json()["status"] == "ok"
                    # Deliver worker signals to Qt before checking UI state.
                    QTimer.singleShot(150, verify_ui)
                except Exception:
                    logging.exception("Smoke test failed")
                    app.exit(1)

            def verify_ui():
                try:
                    assert assistant.bubble.text() == "DeskBuddy smoke test"
                    assert chat.ip_input.text()
                    assert chat.chat_layout.count() >= 3
                    assert assistant.movie.isValid()
                    logging.info("SMOKE_TEST_OK")
                    app.exit(0)
                except Exception:
                    logging.exception("Smoke UI check failed")
                    app.exit(1)
            QTimer.singleShot(200, smoke_test)
        return app.exec()
    except Exception as exc:
        logging.exception("Startup failed")
        if not args.smoke_test:
            QMessageBox.critical(None, "DeskBuddy 启动失败", f"{exc}\n\n请检查配置、端口和日志。")
        return 1
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        if server is not None:
            server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
