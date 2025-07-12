# ui/style.py

from PySide6.QtGui import QFont

def get_mono_font(size=10):
    for name in ["Consolas", "Courier New", "DejaVu Sans Mono", "Monaco", "monospace"]:
        font = QFont(name)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(size)
        if QFont().exactMatch():  # optionally check font availability
            return font
    return QFont("monospace", size)