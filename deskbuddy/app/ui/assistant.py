from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtGui import QMovie, QColor
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSize


class AssistantWindow(QWidget):
    remind_signal = Signal(str, int)

    def __init__(self, gif_path, config=None):
        super().__init__()

        self.config = config or {}
        ui_config = self.config.get("ui", {})
        bubble_config = ui_config.get("bubble", {})
        gif_config = ui_config.get("gif", {})

        self.remind_signal.connect(self._remind_impl)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)

        # Message Bubble
        self.bubble = QLabel(self)
        self.bubble.setWordWrap(True)

        # Apply bubble config
        max_width = bubble_config.get("max_width", 200)
        padding = bubble_config.get("padding", 12)
        font_size = bubble_config.get("font_size", 14)

        self.bubble.setMaximumWidth(max_width)
        self.bubble.setStyleSheet(f"""
            QLabel {{
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
                padding: {padding}px;
                color: #333333;
                font-family: "Microsoft YaHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei", "Segoe UI", sans-serif;
                font-size: {font_size}px;
                font-weight: 500;
            }}
        """)

        # Shadow for bubble
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.bubble.setGraphicsEffect(shadow)

        self.bubble.hide() # Start hidden
        self.layout.addWidget(self.bubble)

        # Character GIF
        self.gif_label = QLabel(self)
        self.movie = QMovie(gif_path)

        # Limit GIF size
        if self.movie.isValid():
            self.movie.jumpToFrame(0)
            size = self.movie.currentImage().size()

            gif_max_w = gif_config.get("max_width", 250)
            gif_max_h = gif_config.get("max_height", 250)

            if size.isValid() and (size.width() > gif_max_w or size.height() > gif_max_h):
                new_size = size.scaled(gif_max_w, gif_max_h, Qt.KeepAspectRatio)
                self.movie.setScaledSize(new_size)

        self.gif_label.setMovie(self.movie)
        self.movie.start()

        # Center the GIF
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.gif_label)

        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.hide)

    def remind(self, text, duration=5000):
        self.remind_signal.emit(text, duration)

    def start_greeting(self):
        self.bubble.hide()
        self.show()
        self.raise_()
        # Show for 4 seconds then hide
        self.hide_timer.start(4000)

    @Slot(str, int)
    def _remind_impl(self, text, duration):
        self.bubble.setText(text)
        self.bubble.show()
        self.show()
        self.raise_()
        self.hide_timer.start(duration)
