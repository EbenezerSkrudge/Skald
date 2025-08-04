# ui/widgets/key_capture_edit.py

from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt
from ui.keymap import normalize_key

class KeyCaptureEdit(QLineEdit):
    def keyPressEvent(self, event):
        key_str = normalize_key(event)
        self.setText(key_str)
        event.accept()
