# ui/widgets/numpad_keysequence_edit.py

from PySide6.QtCore    import Qt, QKeyCombination
from PySide6.QtGui     import QKeySequence, QKeyEvent
from PySide6.QtWidgets import QKeySequenceEdit

# Windows VK codes for NumPad 0–9
VK_NUMPAD0 = 0x60
VK_NUMPAD9 = 0x69

class NumpadKeySequenceEdit(QKeySequenceEdit):
    """
    Like QKeySequenceEdit, but:
      - Shows 'Keypad+5' (etc.) for real numpad presses
      - Swallows the corresponding keyRelease to keep the text visible
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable IME so Alt+Numpad doesn’t generate stray characters
        self.setAttribute(Qt.WA_InputMethodEnabled, False)

    def keyPressEvent(self, event: QKeyEvent):
        # if event.isAutoRepeat():
        #     #event.accept()
        #     return

        nvk  = event.nativeVirtualKey()
        mods = event.modifiers()

        # 1) True NumPad digit?
        if VK_NUMPAD0 <= nvk <= VK_NUMPAD9:
            digit = nvk - VK_NUMPAD0

            # turn that int back into a Qt.Key
            raw_value = int(Qt.Key_0) + digit
            qt_key = Qt.Key(raw_value)

            combo = QKeyCombination(
                event.modifiers() | Qt.KeypadModifier,
                qt_key
            )
            self.setKeySequence(QKeySequence(combo))
            event.accept()
            return

        # 2) Otherwise fallback to normal behavior
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        # Swallow *all* releases so QKeySequenceEdit never clears itself
        event.accept()
