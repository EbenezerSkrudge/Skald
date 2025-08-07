# core/managers/keymap_manager.py

import re
from typing            import Any, Dict, List, Optional
from PySide6.QtCore    import QObject, QEvent, Qt
from PySide6.QtGui     import QKeySequence, QKeyEvent
from PySide6.QtWidgets import QApplication
from pony.orm          import db_session, select

from data.models       import KeyBinding


def normalize_key(event: QKeyEvent) -> str:
    """
    Normalize a QKeyEvent to NativeText string.
    Preserves distinction between top-row and keypad digits.
    Encodes keypad digits as "Num+..." to match user bindings.
    """
    k = event.key()
    mods = event.modifiers().value
    code = mods | k

    # Generate base sequence
    seq = QKeySequence(code).toString(QKeySequence.NativeText)

    # If keypad modifier is active and key is 0–9, prefix with "Num+"
    if Qt.Key_0 <= k <= Qt.Key_9 and (event.modifiers() & Qt.KeypadModifier):
        parts = seq.split("+")
        if "Num" not in parts:
            parts.insert(0, "Num")
        seq = "+".join(parts)

    return seq


class KeymapManager(QObject):
    """
    Watches for key presses, looks up user bindings (static and dynamic),
    and dispatches the mapped command to the MUD. Supports:
      - wildcard directions like "north*" → matches north, northup, northdown
      - cardinal/diagonal abbreviations
      - disambiguation menus on multiple exits
    """
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.enabled = True

        self._keymap: Dict[str,str] = {}

        self._pending_choices: Optional[List[str]]    = None
        self._pending_template: Optional[str]         = None
        self._pending_base: Optional[str]             = None

        self.reload()
        QApplication.instance().installEventFilter(self)

    @db_session
    def _load_db_bindings(self) -> Dict[str,str]:
        return {
            QKeySequence(kb.key)
              .toString(QKeySequence.NativeText): kb.command
            for kb in select(k for k in KeyBinding)
        }

    def reload(self):
        self._keymap = self._load_db_bindings()

    def eventFilter(self, obj: Any, event: QEvent) -> bool:
        if event.type() != QEvent.KeyPress:
            return super().eventFilter(obj, event)

        ev: QKeyEvent = event

        # ——— 1) Disambiguation mode —————————————————————————————
        if self._pending_choices is not None:
            if ev.isAutoRepeat():
                return True

            key = ev.key()
            if key == Qt.Key_Escape:
                self._clear_pending()
                event.accept()
                return True

            digit = None
            if Qt.Key_1 <= key <= Qt.Key_9:
                digit = key - Qt.Key_0
            elif Qt.Key_1 <= key <= Qt.Key_9 and (ev.modifiers() & Qt.KeypadModifier):
                digit = key - Qt.Key_0

            if digit:
                idx = digit - 1
                if 0 <= idx < len(self._pending_choices):
                    choice  = self._pending_choices[idx]
                    tmpl    = self._pending_template or ""
                    base    = self._pending_base or ""
                    # replace "north*" with the chosen exit
                    cmd     = tmpl.replace(f"{base}*", choice)
                    self.app.send_to_mud(cmd)

                self._clear_pending()
                event.accept()
                return True

            self._clear_pending()
            event.accept()
            return True

        # ——— 2) Normal key‐map mode ————————————————————————————
        if not self.enabled:
            return super().eventFilter(obj, event)

        key_str = normalize_key(ev)
        cmd_raw = self._keymap.get(key_str)
        if not cmd_raw:
            return super().eventFilter(obj, event)

        # look for wildcard pattern "north*"
        m = re.search(r'([A-Za-z]+)\*', cmd_raw)
        if m:
            base    = m.group(1)
            matches = self._get_direction_matches(base)

            if len(matches) == 0:
                # no GMCP exits, send "north" fallback
                final_cmd = cmd_raw.replace(f"{base}*", base)
                self.app.send_to_mud(final_cmd)
                event.accept()
                return True

            if len(matches) == 1:
                # only one match, auto‐send
                final_cmd = cmd_raw.replace(f"{base}*", matches[0])
                self.app.send_to_mud(final_cmd)
                event.accept()
                return True

            # multiple matches, prompt user
            self._pending_choices  = matches
            self._pending_template = cmd_raw
            self._pending_base     = base
            self._show_disambiguation(matches)
            event.accept()
            return True

        # no wildcard, send as‐is
        self.app.send_to_mud(cmd_raw)
        event.accept()
        return True

    def _get_direction_matches(self, base: str) -> List[str]:
        """
        Return only those GMCP exits that start with `base` and
        have an empty, 'up', or 'down' suffix. Excludes diagonals.
        """
        raw_exits = self._fetch_raw_exits()
        exit_map  = {e.lower(): e for e in raw_exits}
        lower_exits = set(exit_map.keys())
        b = base.lower()

        matches: List[str] = []
        for le in lower_exits:
            if le.startswith(b):
                suffix = le[len(b):]
                if suffix in ('', 'up', 'down'):
                    matches.append(exit_map[le])
        return matches

    def _fetch_raw_exits(self) -> List[str]:
        gmcp = self.app.gmcp_data

        # Room.Info.exits may still be a list
        info = gmcp.get("Room.Info")
        if isinstance(info, dict):
            ex = info.get("exits")
            if isinstance(ex, dict):
                return list(ex.keys())
            if isinstance(ex, list):
                return ex

        # LID.exits is now a dict of {direction: terrain, ...}
        lid = gmcp.get("LID")
        if isinstance(lid, dict):
            ex = lid.get("exits")
            if isinstance(ex, dict):
                return list(ex.keys())
            if isinstance(ex, list):
                return ex

        return []

    def _show_disambiguation(self, choices: List[str]):
        cons = self.app.main_window.console
        cons.echo("There are multiple exits in that direction:")
        for i, c in enumerate(choices, start=1):
            cons.echo(f"{i}: {c}")

    def _clear_pending(self):
        self._pending_choices  = None
        self._pending_template = None
        self._pending_base     = None