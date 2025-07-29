# ui/keymap.py

from typing import Dict, List

from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import QApplication

# Map keypad digits to cardinal directions
_NUMPAD_BASE = {
    Qt.Key_1: "southwest", Qt.Key_2: "south", Qt.Key_3: "southeast",
    Qt.Key_4: "west", Qt.Key_6: "east",
    Qt.Key_7: "northwest", Qt.Key_8: "north", Qt.Key_9: "northeast",
}

# Default key bindings
DEFAULT_KEYMAP = {
    Qt.Key_5: {"action": "look"},
    Qt.Key_Plus: {"action": "vertical", "dir": "up"},
    Qt.Key_Minus: {"action": "vertical", "dir": "down"},
    Qt.Key_0: {"action": "special"},
    **{key: {"action": "cardinal", "base": base} for key, base in _NUMPAD_BASE.items()},
}


class KeyMapper(QObject):
    """
    Intercepts NUMPAD key presses and converts them to game commands.
    """

    def __init__(self, app, keymap: Dict[int, dict] = None):
        super().__init__()
        self.app = app
        self.keymap = keymap or DEFAULT_KEYMAP
        self._pending: Dict[int, str] = {}

    def install(self):
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() != QEvent.KeyPress:
            return super().eventFilter(obj, event)

        key = event.key()
        mods = event.modifiers()

        if self._pending:
            if (mods & Qt.KeypadModifier) and Qt.Key_1 <= key <= Qt.Key_9:
                self._handle_pending_choice(key)
            else:
                self._cancel_selection()
            return True

        if not (mods & Qt.KeypadModifier):
            return super().eventFilter(obj, event)

        conf = self.keymap.get(key)
        if conf:
            self._handle(conf)
            return True

        return super().eventFilter(obj, event)

    def _handle_pending_choice(self, key: int):
        idx = key - Qt.Key_0
        cmd = self._pending.pop(idx, None)
        if cmd:
            self.app.send_to_mud(cmd)
            self._pending.clear()
        else:
            self._cancel_selection()

    def _cancel_selection(self):
        self._pending.clear()
        self._echo("Selection cancelled.")

    def _prompt_options(self, options: List[str]):
        unique = list(dict.fromkeys(options))  # deduplicates and preserves order
        self._pending = {i + 1: cmd for i, cmd in enumerate(unique)}
        lines = ["Multiple exits – choose one:"] + [f"  {i}) {cmd}" for i, cmd in self._pending.items()]
        self._echo("\n".join(lines))

    def _echo(self, text: str):
        self.app.main_window.console.echo(text)

    def _handle(self, conf: dict):
        lid = self.app.gmcp_data.get("LID", {}) or {}
        exits = {**lid.get("links", {}), **lid.get("exits", {})}
        keys = list(exits.keys())

        action = conf.get("action")

        if action == "look":
            self.app.send_to_mud("look")

        elif action == "vertical":
            if conf["dir"] in keys:
                self.app.send_to_mud(conf["dir"])

        elif action == "special":
            cardinals = set(_NUMPAD_BASE.values())
            specials = [e for e in keys if not e.rstrip("up").rstrip("down") in cardinals and e not in ("up", "down")]
            if len(specials) == 1:
                self.app.send_to_mud(specials[0])
            elif specials:
                self._prompt_options(specials)

        elif action == "cardinal":
            base = conf.get("base")
            variants = [base, f"{base}up", f"{base}down"]
            matches = [v for v in variants if v in keys]
            if len(matches) == 1:
                self.app.send_to_mud(matches[0])
            elif matches:
                self._prompt_options(matches)
