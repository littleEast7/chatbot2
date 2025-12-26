import sys
import threading
import argparse
import os
import uuid
import shutil
from PySide6.QtWidgets import QApplication

from app.config import load_config
from app.ui.assistant import AssistantWindow
from app.ui.chat import ChatWindow
from app.scheduler import start_scheduler
from app.server import start_server


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="DeskBuddy")
    parser.add_argument("--port", type=int, help="Server port to listen on")
    args, unknown = parser.parse_known_args()

    # Determine config file
    config_path = "config.yaml"
    if args.port:
        config_path = f"config_{args.port}.yaml"
        if not os.path.exists(config_path):
            if os.path.exists("config.yaml"):
                shutil.copy("config.yaml", config_path)
            else:
                # Create empty or default if needed, but load_config might fail if file missing
                pass

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        # Fallback or create default
        config = {"server": {"host": "0.0.0.0", "port": 9000}, "ui": {}}

    # Ensure user_id exists
    if "user_id" not in config:
        config["user_id"] = uuid.uuid4().hex
        # Save it back immediately
        with open(config_path, "w", encoding="utf-8") as f:
            import yaml
            yaml.dump(config, f, allow_unicode=True)

    # Override port if provided
    if args.port:
        config["server"]["port"] = args.port
        # Also update window title to show port for easier identification
        window_title_suffix = f" (Port: {args.port})"
    else:
        window_title_suffix = ""

    # Attempt to fix input method issues on Linux (e.g. Sougou/Fcitx)
    if sys.platform.startswith("linux"):
        # Check existing environment variables
        xmodifiers = os.environ.get("XMODIFIERS", "")

        if "@im=fcitx" in xmodifiers:
            os.environ.setdefault("QT_IM_MODULE", "fcitx")
            os.environ.setdefault("GTK_IM_MODULE", "fcitx")
        elif "@im=ibus" in xmodifiers:
            os.environ.setdefault("QT_IM_MODULE", "ibus")
            os.environ.setdefault("GTK_IM_MODULE", "ibus")
        else:
            # Default fallback to fcitx as requested by user (Sougou usually uses fcitx)
            os.environ.setdefault("QT_IM_MODULE", "fcitx")
            os.environ.setdefault("GTK_IM_MODULE", "fcitx")
            os.environ.setdefault("XMODIFIERS", "@im=fcitx")

    app = QApplication(sys.argv)

    # Ensure app quits when the last visible window (ChatWindow) is closed
    # AssistantWindow might be hidden, so it shouldn't prevent quit if it's the only one left?
    # Actually AssistantWindow is a Tool window, so it might not count.
    # Let's be explicit.

    # Calculate position (Bottom Right)
    screen_geometry = app.primaryScreen().availableGeometry()
    screen_width = screen_geometry.width()
    screen_height = screen_geometry.height()

    # Fixed width for the assistant window
    window_width = 300
    # Height can vary, but we set a reasonable max or initial height
    window_height = 400

    x = screen_width - window_width - 20
    y = screen_height - window_height - 20

    assistant = AssistantWindow(
        gif_path="assets/assistant.gif",
        config=config
    )
    assistant.resize(window_width, window_height)
    assistant.move(x, y)
    assistant.start_greeting()

    # Chat Window (Main Control Interface)
    chat_window = ChatWindow(config, config_path=config_path)
    if window_title_suffix:
        chat_window.setWindowTitle(chat_window.windowTitle() + window_title_suffix)
    chat_window.show()

    # 定时任务
    scheduler = start_scheduler(config, assistant)

    # HTTP server（后台线程）
    threading.Thread(
        target=start_server,
        args=(config, assistant, chat_window),
        daemon=True,
    ).start()

    # Graceful exit
    def cleanup():
        print("Shutting down scheduler...")
        scheduler.shutdown()
        print("Bye!")

    app.aboutToQuit.connect(cleanup)

    if sys.platform.startswith("linux"):
        print("提示: 如果无法使用搜狗输入法，请尝试运行: export QT_IM_MODULE=fcitx && python main.py")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
