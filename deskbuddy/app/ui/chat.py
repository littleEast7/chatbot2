from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QPushButton, QLabel, QFrame, QApplication, QScrollArea,
                               QSizePolicy, QGraphicsDropShadowEffect, QFileDialog)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPainterPath
import requests
import threading
import os
import json
import hashlib
import logging
from pathlib import Path
from app.config import save_config as persist_config
from app.paths import data_dir
from app.network import peer_target, sender_address as format_sender
from app.server import MAX_AVATAR_BYTES
import base64

class ChatWindow(QWidget):
    # Signal to update UI from background threads
    message_received = Signal(str, str)
    connection_status_changed = Signal(bool, str)
    avatar_received = Signal(str, str, str)

    def __init__(self, config, config_path="config.yaml"):
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.setWindowTitle("DeskBuddy")
        self.resize(380, 700)
        self.setStyleSheet("background-color: #FFFFFF;")

        # Avatar state
        # "my_avatar" is the user's own avatar
        self.current_avatar_path = self.config.get("my_avatar", "")
        # "friend_avatar" is the connected friend's avatar (received via handshake)
        self.friend_avatar_path = None
        self.default_avatar_color = "#E5E5EA"
        self.avatar_received.connect(self._save_friend_avatar, Qt.QueuedConnection)
        self._network_slots = threading.BoundedSemaphore(4)


        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Header (Glassmorphism style simulation) ---
        self.header = QFrame()
        self.header.setFixedHeight(80)
        self.header.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-bottom: 1px solid #E5E5EA;
            }
        """)

        # Use QHBoxLayout for the requested layout: Avatar (Left) - Title (Center) - IP (Right)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 10, 15, 10)
        header_layout.setSpacing(10)

        # 1. Left: Avatar (Clickable)
        self.avatar_btn = QPushButton()
        self.avatar_btn.setFixedSize(40, 40)
        self.avatar_btn.setCursor(Qt.PointingHandCursor)
        self.avatar_btn.clicked.connect(self.change_avatar)
        # Remove border and padding to avoid white obstruction
        self.avatar_btn.setStyleSheet("border: none; padding: 0px; background-color: transparent;")

        header_layout.addWidget(self.avatar_btn)

        header_layout.addStretch()

        # 2. Center: Title
        title = QLabel("DeskBuddy")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #000000; border: none; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 3. Right: IP Input and Link Button Container
        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(10)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("IP:Port")
        self.ip_input.setText(self.config.get("target_ip", ""))
        self.ip_input.setAlignment(Qt.AlignCenter)
        self.ip_input.setFixedWidth(120)
        self.ip_input.setStyleSheet("""
            QLineEdit {
                background-color: #F2F2F7;
                border: none;
                border-radius: 8px;
                padding: 4px;
                color: #8E8E93;
                font-size: 12px;
            }
            QLineEdit:focus {
                background-color: #E5E5EA;
                color: #000000;
            }
        """)
        # Save IP when changed
        self.ip_input.editingFinished.connect(self.save_config)
        self.right_layout.addWidget(self.ip_input)

        # 4. Link Button
        self.link_btn = QPushButton("🔗")
        self.link_btn.setFixedSize(30, 30)
        self.link_btn.setCursor(Qt.PointingHandCursor)
        self.link_btn.setToolTip("连接对方 (握手)")
        self.link_btn.clicked.connect(self.send_handshake)
        self.link_btn.setStyleSheet("""
            QPushButton {
                background-color: #34C759;
                color: white;
                border-radius: 15px;
                font-size: 14px;
                border: none;
            }
            QPushButton:pressed {
                background-color: #248A3D;
            }
        """)
        self.right_layout.addWidget(self.link_btn)

        header_layout.addWidget(self.right_container)

        # 5. Connected Avatar (Hidden by default)
        self.connected_avatar = QPushButton()
        self.connected_avatar.setFixedSize(40, 40)
        self.connected_avatar.setStyleSheet("border: none; background-color: transparent;")
        self.connected_avatar.setToolTip("点击切换连接地址")
        self.connected_avatar.clicked.connect(lambda: self._handle_connection_status(False, ""))
        self.connected_avatar.hide()
        header_layout.addWidget(self.connected_avatar)

        # Initial update of avatars
        self.update_avatar_display()

        layout.addWidget(self.header)

        # --- Chat Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: #FFFFFF; border: none; }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #D1D1D6;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(15, 15, 15, 15)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addStretch() # Push messages to bottom if few

        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area)

        # --- Input Area (Glassmorphism style simulation) ---
        self.input_area = QFrame()
        self.input_area.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-top: 1px solid #E5E5EA;
            }
        """)
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(15, 10, 15, 20) # Extra bottom margin for "mobile" feel
        input_layout.setSpacing(10)

        # Input Box
        self.msg_input = QLineEdit()
        self.msg_input.setAttribute(Qt.WA_InputMethodEnabled, True)
        self.msg_input.setPlaceholderText("iMessage")
        self.msg_input.returnPressed.connect(self.send_message)
        self.msg_input.setFixedHeight(36)
        self.msg_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #C6C6C8;
                border-radius: 18px;
                padding-left: 15px;
                padding-right: 15px;
                font-size: 15px;
                color: #000000;
            }
            QLineEdit:focus {
                border: 1px solid #007AFF;
            }
        """)
        input_layout.addWidget(self.msg_input)

        # Send Button
        self.send_btn = QPushButton("↑")
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 16px;
                font-weight: bold;
                font-size: 18px;
                border: none;
                padding-bottom: 2px;
            }
            QPushButton:pressed {
                background-color: #0056B3;
            }
        """)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(self.input_area)

        # Connect signal
        self.message_received.connect(self._append_incoming_message)
        self.connection_status_changed.connect(self._handle_connection_status)

    def send_handshake(self):
        target_ip = self.ip_input.text().strip()
        if not target_ip:
            self.add_message_item("请先输入对方IP地址", is_me=False, is_system=True)
            return

        self.add_message_item(f"正在连接 {target_ip}...", is_me=False, is_system=True)
        self._start_worker(self._send_handshake_http, target_ip)

    def _send_handshake_http(self, address):
        try:
            target = peer_target(address)

            url = f"http://{target}/handshake"
            local_port = self.config.get("server", {}).get("port", 9000)
            user_id = self.config.get("user_id")

            # Prepare avatar data
            avatar_data = None
            if self.current_avatar_path and os.path.exists(self.current_avatar_path):
                try:
                    with open(self.current_avatar_path, "rb") as f:
                        content = f.read(MAX_AVATAR_BYTES + 1)
                        if len(content) <= MAX_AVATAR_BYTES:
                            avatar_data = base64.b64encode(content).decode('ascii')
                except Exception as e:
                    print(f"Failed to read avatar: {e}")

            payload = {
                "port": local_port,
                "avatar": avatar_data,
                "user_id": user_id
            }

            data = self._post_peer(url, payload)
            friend_avatar_data = data.get("avatar")
            friend_user_id = data.get("user_id")
            if friend_avatar_data is not None and not isinstance(friend_avatar_data, str):
                raise ValueError("对方头像数据格式错误")
            if friend_user_id is not None and (not isinstance(friend_user_id, str) or len(friend_user_id) > 128):
                raise ValueError("对方用户 ID 格式错误")
            self.avatar_received.emit(friend_avatar_data or "", friend_user_id or "", target)
            self.message_received.emit("[系统] 连接成功! 对方已收到您的地址。", "")
            self.connection_status_changed.emit(True, target)

        except Exception as e:
            self.message_received.emit(f"[系统] 连接失败: {e}", "")

    def on_handshake_received(self, sender_ip, sender_port, avatar_data=None, user_id=None):
        sender_address = format_sender(sender_ip, sender_port)
        self.avatar_received.emit(avatar_data or "", user_id or "", sender_address)

        # Update UI via signal (reuse message_received for simplicity or create new one)
        # We use a special system message format to trigger config update
        self.message_received.emit(f"[系统] 收到来自 {sender_address} 的连接请求，已自动配置。", sender_address)
        self.connection_status_changed.emit(True, sender_address)

    def change_avatar(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            if not Path(file_path).is_file() or Path(file_path).stat().st_size > MAX_AVATAR_BYTES or QPixmap(file_path).isNull():
                self.add_message_item("请选择有效且小于 2 MiB 的图片", False, True)
                return
            self.current_avatar_path = file_path
            self.config["my_avatar"] = file_path
            self.update_avatar_display()
            self.save_config()

    def save_config(self):
        # Update IP in config
        self.config["target_ip"] = self.ip_input.text().strip()

        # Persist to file
        try:
            persist_config(self.config, self.config_path)
        except Exception as e:
            logging.exception("Error saving config")
            self.add_message_item(f"配置保存失败: {e}", False, True)

    @Slot(str, str, str)
    def _save_friend_avatar(self, avatar_data, user_id, ip_port_str):
        try:
            if not avatar_data:
                self.friend_avatar_path = None
                self.update_avatar_display()
                return
            if len(avatar_data) > 4 * ((MAX_AVATAR_BYTES + 2) // 3):
                raise ValueError("头像过大")
            content = base64.b64decode(avatar_data, validate=True)
            if len(content) > MAX_AVATAR_BYTES:
                raise ValueError("头像过大")
            pixmap = QPixmap()
            if not pixmap.loadFromData(content):
                raise ValueError("头像不是有效图片")
            cache_dir = data_dir() / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Never use untrusted peer IDs as filesystem paths.
            digest = hashlib.sha256((user_id or ip_port_str).encode()).hexdigest()
            filepath = cache_dir / f"friend_avatar_{digest}.png"
            if not pixmap.save(str(filepath), "PNG"):
                raise OSError("头像缓存无法写入")
            self.friend_avatar_path = str(filepath)
            self.update_avatar_display()
        except Exception as exc:
            logging.warning("Invalid friend avatar: %s", exc)

    def _post_peer(self, url, payload):
        response = requests.post(url, json=payload, headers=self._auth_headers(),
                                 timeout=3, stream=True)
        try:
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > 3 * 1024 * 1024:
                    raise ValueError("对方响应过大")
                chunks.append(chunk)
            data = json.loads(b"".join(chunks))
            if not isinstance(data, dict) or data.get("status") != "ok":
                raise ValueError("对方返回了无效响应")
            return data
        finally:
            response.close()

    def _auth_headers(self):
        token = self.config.get("server", {}).get("token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _start_worker(self, callback, *args):
        if not self._network_slots.acquire(blocking=False):
            self.add_message_item("请求过多，请稍后重试", False, True)
            return False
        def run():
            try:
                callback(*args)
            finally:
                self._network_slots.release()
        threading.Thread(target=run, daemon=True, name="DeskBuddy-peer").start()
        return True

    def update_avatar_display(self):
        # Update the header button (My Avatar)
        pixmap = self.get_circle_pixmap(self.current_avatar_path, QSize(40, 40))
        if pixmap:
            self.avatar_btn.setIcon(QIcon(pixmap))
            self.avatar_btn.setIconSize(QSize(40, 40))
        else:
            # Default gray circle
            self.avatar_btn.setIcon(QIcon())
            style = f"""
                QPushButton {{
                    border: none; 
                    border-radius: 20px; 
                    background-color: {self.default_avatar_color};
                }}
            """
            self.avatar_btn.setStyleSheet(style)

        # Update connected avatar (Friend's Avatar)
        friend_pixmap = self.get_circle_pixmap(self.friend_avatar_path, QSize(40, 40))
        if friend_pixmap:
            self.connected_avatar.setIcon(QIcon(friend_pixmap))
            self.connected_avatar.setIconSize(QSize(40, 40))
        else:
            self.connected_avatar.setStyleSheet(f"""
                QPushButton {{
                    border: none; 
                    border-radius: 20px; 
                    background-color: {self.default_avatar_color};
                }}
            """)
            self.connected_avatar.setIcon(QIcon())

    def get_circle_pixmap(self, image_path, size):
        if not image_path or not os.path.exists(image_path):
            return None

        target = QPixmap(size)
        target.fill(Qt.transparent)

        p = QPixmap(image_path)
        if p.isNull():
            return None

        # Scale keeping aspect ratio to cover
        scaled = p.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        # Crop center
        x = (scaled.width() - size.width()) // 2
        y = (scaled.height() - size.height()) // 2

        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size.width(), size.height())
        painter.setClipPath(path)
        painter.drawPixmap(-x, -y, scaled)
        painter.end()
        return target

    def send_message(self):
        text = self.msg_input.text().strip()
        target_ip = self.ip_input.text().strip()

        if not text:
            return
        try:
            peer_target(target_ip)
        except ValueError as exc:
            self.add_message_item(str(exc), False, True)
            return
        if not target_ip:
            self.add_message_item("请先输入对方IP地址", is_me=False, is_system=True)
            return

        if len(text) > 10000:
            self.add_message_item("消息最多 10000 个字符", False, True)
            return
        if not self._start_worker(self._send_http, target_ip, text):
            return

        # Clear input only when the outgoing worker has been accepted.
        self.msg_input.clear()

        # Show locally
        self.add_message_item(text, is_me=True)


    def _send_http(self, address, text):
        try:
            target = peer_target(address)

            url = f"http://{target}/remind"
            local_port = self.config.get("server", {}).get("port", 9000)
            self._post_peer(url, {"text": text, "port": local_port})
        except Exception as e:
            self.message_received.emit(f"[系统] 发送失败: {e}", "")
            self.connection_status_changed.emit(False, "")

    def add_message_item(self, text, is_me, is_system=False):
        item_widget = QWidget()
        item_widget.setStyleSheet("background: transparent;")
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(8)

        if is_system:
            label = QLabel(text)
            label.setTextFormat(Qt.PlainText)
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #8E8E93; font-size: 12px; font-style: italic; background: transparent;")
            item_layout.addWidget(label)
        else:
            # Avatar (Only for other)
            if not is_me:
                avatar = QLabel()
                avatar.setFixedSize(35, 35)

                # Try to load friend avatar
                pixmap = self.get_circle_pixmap(self.friend_avatar_path, QSize(35, 35))
                if pixmap:
                    avatar.setPixmap(pixmap)
                    avatar.setStyleSheet("background: transparent;")
                else:
                    avatar.setStyleSheet(f"""
                        background-color: {self.default_avatar_color};
                        border-radius: 17px;
                        border: 1px solid #D1D1D6;
                    """)

                item_layout.addWidget(avatar)
                item_layout.setAlignment(avatar, Qt.AlignBottom)

            # Bubble
            bubble = QLabel(text)
            bubble.setTextFormat(Qt.PlainText)
            bubble.setWordWrap(True)
            bubble.setMaximumWidth(240)

            # Font setup
            font = QFont()
            font.setFamilies(["PingFang SC", "Heiti SC", "Microsoft YaHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei", "Arial"])
            font.setPixelSize(15)
            bubble.setFont(font)

            padding = "10px 14px"
            if is_me:
                bubble.setStyleSheet(f"""
                    QLabel {{
                        background-color: #007AFF;
                        color: white;
                        border-radius: 18px;
                        padding: {padding};
                        border-bottom-right-radius: 4px;
                    }}
                """)
                item_layout.addStretch()
                item_layout.addWidget(bubble)
            else:
                bubble.setStyleSheet(f"""
                    QLabel {{
                        background-color: #E9E9EB;
                        color: black;
                        border-radius: 18px;
                        padding: {padding};
                        border-bottom-left-radius: 4px;
                    }}
                """)
                item_layout.addWidget(bubble)
                item_layout.addStretch()

        self.chat_layout.addWidget(item_widget)
        # Bound widget memory for long-running sessions.
        while self.chat_layout.count() > 501:
            old = self.chat_layout.takeAt(1).widget()
            if old is not None:
                old.deleteLater()

        # Scroll to bottom
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    @Slot(str, str)
    def _append_incoming_message(self, text, sender_address):
        if sender_address:
            # Auto-configure target IP if not set
            if not self.ip_input.text().strip():
                self.ip_input.setText(sender_address)
                self.save_config()

        if text.startswith("[系统]"):
            self.add_message_item(text, is_me=False, is_system=True)
        else:
            self.add_message_item(text, is_me=False)

    @Slot(bool, str)
    def _handle_connection_status(self, connected, target_ip):
        if connected:
            self.right_container.hide()
            self.connected_avatar.show()
            if target_ip:
                self.ip_input.setText(target_ip)
                self.save_config()

            # Update the connected avatar icon
            # Use friend_avatar_path here
            pixmap = self.get_circle_pixmap(self.friend_avatar_path, QSize(40, 40))
            if pixmap:
                self.connected_avatar.setIcon(QIcon(pixmap))
                self.connected_avatar.setIconSize(QSize(40, 40))
            else:
                self.connected_avatar.setStyleSheet(f"""
                    QPushButton {{
                        border: none; 
                        border-radius: 20px; 
                        background-color: {self.default_avatar_color};
                    }}
                """)
                self.connected_avatar.setIcon(QIcon())
        else:
            self.right_container.show()
            self.connected_avatar.hide()

    def on_message_received(self, text, sender_ip=None, sender_port=None):
        sender_address = format_sender(sender_ip, sender_port)
        self.message_received.emit(text, sender_address)

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()
