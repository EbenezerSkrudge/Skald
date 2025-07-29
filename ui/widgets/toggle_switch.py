# ui/widgets/toggle_switch.py

from PySide6.QtCore import Qt, Property, QPropertyAnimation, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 28)
        self._checked = True
        self._slider_pos = 1.0

        self._anim = QPropertyAnimation(self, b"slider_pos", self)
        self._anim.setDuration(150)

    # Actual property logic
    @Property(float)
    def slider_pos(self):
        return self._slider_pos

    @slider_pos.setter
    def slider_pos(self, pos):
        self._slider_pos = pos
        self.update()

    @Property(bool)
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, val: bool):
        self.set_checked(val)

    def is_checked(self):
        return self._checked

    def set_checked(self, checked: bool):
        self._checked = checked
        self._anim.stop()
        self._anim.setStartValue(self._slider_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        self.update()

    def toggle(self):
        self.set_checked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bg_rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        knob_diam = self.height() - 6
        knob_x = 3 + self._slider_pos * (self.width() - knob_diam - 6)
        knob_rect = QRectF(knob_x, 3, knob_diam, knob_diam)

        # background color
        bg_color = QColor("#4caf50") if self._checked else QColor("#ccc")
        knob_color = QColor("white")

        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, bg_rect.height() / 2, bg_rect.height() / 2)

        painter.setBrush(QBrush(knob_color))
        painter.drawEllipse(knob_rect)

    def sizeHint(self):
        return self.size()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
            self.toggled.emit(self._checked)
