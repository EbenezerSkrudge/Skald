# ui/keymap.py

from typing import Dict, List, Optional
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from pony.orm import db_session, select
from data.models import KeyBinding
import re

_NUMPAD_BASE = {
    Qt.Key_1: "southwest", Qt.Key_2: "south", Qt.Key_3: "southeast",
    Qt.Key_4: "west",                              Qt.Key_6: "east",
    Qt.Key_7: "northwest", Qt.Key_8: "north", Qt.Key_9: "northeast",
}

_CANONICAL_DIRS = [
    "north", "south", "east", "west",
    "northeast", "northwest", "southeast", "southwest",
    "up", "down"
]

def normalize_key(event: QEvent) -> str:
    parts = []
    mods = event.modifiers()
    if mods & Qt.ControlModifier: parts.append("Ctrl")
    if mods & Qt.ShiftModifier: parts.append("Shift")
    if mods & Qt.AltModifier: parts.append("Alt")
    if mods & Qt.MetaModifier: parts.append("Meta")

    key = event.key()
    key_name = Qt.Key(key).name.replace("Key_", "") if key in Qt.Key.__members__.values() else chr(key)

    if mods & Qt.KeypadModifier:
        if key == 43: key_name = "Numpad+"
        elif key == 45: key_name = "Numpad-"
        elif key_name.isdigit(): key_name = f"Numpad{key_name}"

    parts.append(key_name)
    return "+".join(parts)

def build_default_keymap() -> Dict[str, dict]:
    base = {
        "Numpad5": {"command": "look"},
        "Numpad+": {"command": "*up"},
        "Numpad-": {"command": "*down"},
        "Numpad0": {"command": "special"},
    }
    base.update({
        f"Numpad{Qt.Key(k).name.replace('Key_', '')}": {"command": f"*{base_dir}"}
        for k, base_dir in _NUMPAD_BASE.items()
    })
    return base

@db_session
def load_db_keymap() -> Dict[str, dict]:
    return {kb.key: {"command": kb.command} for kb in select(k for k in KeyBinding)}

def get_effective_keymap() -> Dict[str, dict]:
    keymap = build_default_keymap()
    keymap.update(load_db_keymap())
    return keymap

def build_direction_map(exits: Dict[str, int]) -> Dict[str, str]:
    direction_map = {}
    for canonical in _CANONICAL_DIRS:
        for exit_name in exits:
            # Match if exit_name == canonical or starts with canonical + known suffix
            if exit_name == canonical:
                direction_map[canonical] = exit_name
                break
            suffix = exit_name[len(canonical):]
            if exit_name.startswith(canonical) and suffix in ("up", "down", "in", "out", ""):
                direction_map[canonical] = exit_name
                break
    return direction_map


def resolve_placeholders(cmd: str, exits: Dict[str, int]) -> str:
    if not isinstance(cmd, str):
        return str(cmd)

    direction_map = build_direction_map(exits)

    def repl(match):
        raw = match.group(1)
        return direction_map.get(raw, raw)

    return re.sub(r"\*(\w+)", repl, cmd)

class KeyMapper(QObject):
    def __init__(self, app, keymap: Dict[str, dict] = None):
        super().__init__()
        self.app = app
        self.keymap = keymap or get_effective_keymap()
        self._pending: Dict[int, str] = {}

    def install(self):
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() != QEvent.KeyPress:
            return super().eventFilter(obj, event)

        if self._pending:
            if (event.modifiers() & Qt.KeypadModifier) and Qt.Key_1 <= event.key() <= Qt.Key_9:
                self._handle_pending_choice(event.key())
            else:
                self._cancel_selection()
            return True

        if not (event.modifiers() & Qt.KeypadModifier):
            return super().eventFilter(obj, event)

        key_str = normalize_key(event)
        conf = self.keymap.get(key_str)
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
        unique = list(dict.fromkeys(options))
        self._pending = {i + 1: cmd for i, cmd in enumerate(unique)}
        lines = ["Multiple exits – choose one:"] + [f"  {i}) {cmd}" for i, cmd in self._pending.items()]
        self._echo("\n".join(lines))

    def _echo(self, text: str):
        self.app.main_window.console.echo(text)

    def _handle(self, conf: dict):
        raw_cmd = conf.get("command", "")
        lid = self.app.gmcp_data.get("LID", {}) or {}
        exits = {**lid.get("links", {}), **lid.get("exits", {})}

        if raw_cmd == "special":
            cardinals = set(_NUMPAD_BASE.values())
            specials = [
                e for e in exits
                if not any(e.startswith(c) for c in cardinals)
                and e not in ("up", "down")
            ]
            if len(specials) == 1:
                self.app.send_to_mud(specials[0])
            elif specials:
                self._prompt_options(specials)
            return

        final_cmd = resolve_placeholders(raw_cmd, exits)
        self.app.send_to_mud(final_cmd)

    @staticmethod
    def get_defaults() -> Dict[tuple[str, Optional[str]], str]:
        return {(key, None): conf["command"] for key, conf in build_default_keymap().items()}

    def reload(self):
        self.keymap = get_effective_keymap()
