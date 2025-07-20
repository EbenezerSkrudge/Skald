# ui/keymap.py

from typing            import Dict, List
from PySide6.QtCore    import QObject, QEvent, Qt
from PySide6.QtWidgets import QApplication

# Map keypad digits 1–9 to their base‐cardinal names
_NUMPAD_BASE = {
    Qt.Key_1: "southwest",
    Qt.Key_2: "south",
    Qt.Key_3: "southeast",
    Qt.Key_4: "west",
    Qt.Key_6: "east",
    Qt.Key_7: "northwest",
    Qt.Key_8: "north",
    Qt.Key_9: "northeast",
}

# Default keymap: keypad key → descriptor
DEFAULT_KEYMAP = {
    Qt.Key_5:     {"action": "look"},                                # look
    Qt.Key_Plus:  {"action": "vertical", "dir": "up"},               # up
    Qt.Key_Minus: {"action": "vertical", "dir": "down"},             # down
    Qt.Key_0:     {"action": "special"},                             # in/out/other
    **{
        key: {"action": "cardinal", "base": base}
        for key, base in _NUMPAD_BASE.items()
    },                                                              # 8‐way
}


class KeyMapper(QObject):
    """
    Intercepts NUMPAD KeyPress events and turns them into
    send_to_mud(...) calls based on GMCP.LID["links"] + ["exits"].
    If multiple choices arise, prompts the player and awaits selection.
    """

    def __init__(self, app, keymap: Dict[int, dict] = None):
        super().__init__(None)
        self.app      = app
        self.keymap   = keymap or DEFAULT_KEYMAP
        self._pending: Dict[int, str] = {}

    def install(self):
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() != QEvent.KeyPress:
            return super().eventFilter(obj, event)

        key  = event.key()
        mods = event.modifiers()

        # 1) If awaiting a pending choice, handle it first
        if self._pending:
            if (mods & Qt.KeypadModifier) and (Qt.Key_1 <= key <= Qt.Key_9):
                idx = key - Qt.Key_0
                cmd = self._pending.get(idx)
                if cmd:
                    self._pending.clear()
                    self.app.send_to_mud(cmd)
                else:
                    self._cancel_selection()
            else:
                self._cancel_selection()
            return True

        # 2) Only respond to real NUMPAD keypresses
        if not (mods & Qt.KeypadModifier):
            return super().eventFilter(obj, event)

        conf = self.keymap.get(key)
        if conf:
            self._handle(conf)
            return True

        return super().eventFilter(obj, event)

    def _cancel_selection(self):
        self._pending.clear()
        self._echo("Selection cancelled.")

    def _prompt_options(self, options: List[str]):
        """
        Display numbered options and store them in _pending.
        """
        # dedupe while preserving order
        seen = set()
        opts: List[str] = []
        for opt in options:
            if opt not in seen:
                seen.add(opt)
                opts.append(opt)

        self._pending = {i+1: cmd for i, cmd in enumerate(opts)}
        lines = ["Multiple exits – choose one:"]
        for num, cmd in self._pending.items():
            lines.append(f"  {num}) {cmd}")
        self._echo("\n".join(lines))

    def _echo(self, text: str):
        """
        Replace this with your console‐widget's append method.
        """
        self.app.main_window.console.echo(text)

    def _handle(self, conf: dict):
        """
        Resolve the action descriptor into a MUD command,
        using both 'links' and 'exits' from the LID GMCP payload.
        """
        lid     = self.app.gmcp_data.get("LID", {}) or {}
        links   = lid.get("links", {}) or {}
        exits   = lid.get("exits", {}) or {}
        # merge links + exits, exits overrides on duplicate keys
        all_exits = {**links, **exits}
        keys      = list(all_exits.keys())

        match conf.get("action"):
            case "look":
                self.app.send_to_mud("look")

            case "vertical":
                d = conf.get("dir")
                if d in keys:
                    self.app.send_to_mud(d)

            case "special":
                # collect all non‐cardinal, non‐vertical exits
                cardinals = set(_NUMPAD_BASE.values())
                specials: List[str] = []
                for txt in keys:
                    base = txt.rstrip("up").rstrip("down")
                    if base in ("up", "down") or base in cardinals:
                        continue
                    specials.append(txt)

                if not specials:
                    return
                if len(specials) == 1:
                    self.app.send_to_mud(specials[0])
                else:
                    self._prompt_options(specials)

            case "cardinal":
                base = conf.get("base")
                # consider exactly these three
                variants = [base, f"{base}up", f"{base}down"]
                available = [v for v in variants if v in keys]

                if not available:
                    return
                if len(available) == 1:
                    self.app.send_to_mud(available[0])
                else:
                    self._prompt_options(available)

            case _:
                return