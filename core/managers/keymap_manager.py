# core/managers/keymap_manager.py

from typing import Dict, List, Any
from PySide6.QtCore import QObject, QEvent
from PySide6.QtGui import QKeySequence, QKeyEvent
from PySide6.QtWidgets import QApplication
from pony.orm import db_session, select

from data.models import KeyBinding


def normalize_key(event: QKeyEvent) -> str:
    """
    Turn a QKeyEvent into the same “NativeText” string
    the settings UI uses (e.g. "Ctrl+Shift+S").
    """
    mods = event.modifiers().value
    code = mods | event.key()
    return QKeySequence(code).toString(QKeySequence.NativeText)


class KeymapManager(QObject):
    """
    Listens for key presses, looks up user bindings
    (including dynamic directions/abbreviations),
    and dispatches the mapped command to the MUD.
    """
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.enabled = True
        self._keymap: Dict[str, str] = {}

        self.reload()
        QApplication.instance().installEventFilter(self)

    @db_session
    def _load_db_bindings(self) -> Dict[str, str]:
        """
        Pull KeyBinding rows into a dict:
          { NativeText shortcut: command string }
        """
        return {
            QKeySequence(kb.key)
                .toString(QKeySequence.NativeText): kb.command
            for kb in select(k for k in KeyBinding)
        }

    def reload(self):
        """
        Refresh the in-memory keymap from the database.
        Call this after the user saves new bindings.
        """
        self._keymap = self._load_db_bindings()

    def eventFilter(self, obj: Any, event: QEvent) -> bool:
        """
        Intercept KeyPress events when enabled.
        Normalize, look up in keymap, resolve directions,
        send to MUD, and consume the event.
        """
        if not self.enabled or event.type() != QEvent.KeyPress:
            return super().eventFilter(obj, event)

        key_str = normalize_key(event)
        cmd = self._keymap.get(key_str)
        if not cmd:
            return super().eventFilter(obj, event)

        if cmd.startswith('*'):
            cmd = self._resolve_direction(cmd[1:])

        self.app.send_to_mud(cmd)
        return True

    def _resolve_direction(self, base: str) -> str:
        """
        Resolve a base token or abbreviation against the
        current GMCP exit list in app.gmcp_data.
        Priority:
          1. Exact match
          2. Common cardinal/diagonal abbreviations
          3. Shortest prefix match
          4. Fallback to base
        """
        raw_exits: List[str] = []

        # Try Room.Info.exits (if provided)
        room = self.app.gmcp_data.get("Room.Info")
        if isinstance(room, dict):
            raw_exits = room.get("exits", [])

        # Fallback on LID.exits
        if not raw_exits:
            lid = self.app.gmcp_data.get("LID", {})
            if isinstance(lid, dict):
                raw_exits = lid.get("exits", [])

        # Build case‐insensitive lookup
        exit_map = {e.lower(): e for e in raw_exits}
        lower_exits = set(exit_map.keys())
        b = base.lower()

        # 1) Exact match
        if b in lower_exits:
            return exit_map[b]

        # 2) Standard abbreviations
        abbr_map = {
            'n':  'north',     's':  'south',
            'e':  'east',      'w':  'west',
            'ne': 'northeast', 'nw': 'northwest',
            'se': 'southeast', 'sw': 'southwest',
            'u':  'up',        'd':  'down',
        }
        if b in abbr_map:
            full = abbr_map[b].lower()
            if full in lower_exits:
                return exit_map[full]

        # 3) Shortest prefix match
        matches = [le for le in lower_exits if le.startswith(b)]
        if matches:
            best = min(matches, key=len)
            return exit_map[best]

        # 4) Give up — return the raw base
        return base