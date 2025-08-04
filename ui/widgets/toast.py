from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve

class Toast(QWidget):
    def __init__(self, message, duration=2000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Pale yellow square, no rounded corners
        self.setStyleSheet("""
            background: #fff8c4;
            color: #333;
            padding: 10px;
            border: 1px solid #ccc;
            font-size: 13px;
        """)

        label = QLabel(message, self)
        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.setContentsMargins(10, 6, 10, 6)

        # Opacity effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # Fade-in animation
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.InOutQuad)

        # Fade-out animation
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_out.finished.connect(self.close)

        self.adjustSize()
        QTimer.singleShot(duration, self.start_fade_out)

    def show(self):
        super().show()
        self.fade_in.start()

    def start_fade_out(self):
        self.fade_out.start()