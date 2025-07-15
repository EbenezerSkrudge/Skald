# core/timer_manager.py

import re
from typing       import List, Optional
from pony.orm     import db_session
from PySide6.QtCore import QObject, QTimer
from core.context import Context
from data.models  import Script

class TimerManager(QObject):
    """
    Manages user‐defined timers: Python code blocks that fire every N ms.
    API mirrors TriggerManager/AliasManager: create(), update(), delete(),
    toggle(), get_all(), find(), plus clear_all()/reload() for in-memory.
    """

    def __init__(self, app):
        super().__init__()
        self._ctx    = Context(app)
        self._timers = {}  # name -> QTimer
        self.reload()

    # ─── Public Reload / Clear ───────────────────────────────

    def clear_all(self):
        """Stop and delete every QTimer."""
        for t in self._timers.values():
            t.stop()
            t.deleteLater()
        self._timers.clear()

    def reload(self):
        """Clear then load all enabled 'timer' Scripts from the DB."""
        self.clear_all()
        self._load_all_from_db()

    # ─── Internal DB Loader ───────────────────────────────────

    @db_session
    def _load_all_from_db(self):
        for rec in Script.select(lambda s: s.category=="timer" and s.enabled):
            ms = rec.interval or 0
            if ms <= 0:
                continue
            self._register_timer(rec.name, ms, rec.code)

    def _register_timer(self, name: str, ms: int, code: str):
        """Create & start one QTimer for this script."""
        # compile user code
        code_obj = compile(code or "", f"<timer:{name}>", "exec")

        def on_timeout():
            exec(
                code_obj, {},
                {
                    "ctx":  self._ctx,
                    "echo": self._ctx.echo,
                    "send": self._ctx.send,
                }
            )

        timer = QTimer(self)
        timer.setInterval(ms)
        timer.timeout.connect(on_timeout)
        timer.start()
        self._timers[name] = timer

    def _unregister_timer(self, name: str):
        """Stop & remove a single timer by name."""
        t = self._timers.pop(name, None)
        if t:
            t.stop()
            t.deleteLater()

    # ─── Persistence & CRUD API ──────────────────────────────

    @db_session
    def get_all(self) -> List[Script]:
        return list(
            Script
            .select(lambda s: s.category=="timer")
            .order_by(Script.priority)
        )

    @db_session
    def find(self, name: str) -> Optional[Script]:
        return Script.select(
            lambda s: s.name==name and s.category=="timer"
        ).first()

    @db_session
    def create(
        self,
        name: str,
        ms: int,
        code: str,
        priority: int = 0,
        enabled: bool = True
    ) -> Script:
        rec = Script(
            name     = name,
            category = "timer",
            interval = ms,
            code     = code,
            enabled  = enabled,
            priority = priority
        )
        rec.flush()
        if enabled:
            self._register_timer(name, ms, code)
        return rec

    @db_session
    def update(
        self,
        old_name: str,
        name: str,
        ms: int,
        code: str,
        priority: int,
        enabled: bool
    ) -> Optional[Script]:
        rec = self.find(old_name)
        if not rec:
            return None

        # update fields
        rec.name     = name
        rec.interval = ms
        rec.code     = code
        rec.priority = priority
        rec.enabled  = enabled
        rec.flush()

        # restart timer under new settings
        self._unregister_timer(old_name)
        if enabled and ms > 0:
            self._register_timer(name, ms, code)

        return rec

    @db_session
    def delete(self, name: str):
        rec = self.find(name)
        if rec:
            rec.delete()
        self._unregister_timer(name)

    @db_session
    def toggle(self, name: str) -> Optional[bool]:
        rec = self.find(name)
        if not rec:
            return None

        rec.enabled = not rec.enabled
        rec.flush()

        if rec.enabled:
            # start timer
            ms = rec.interval or 0
            if ms > 0:
                self._register_timer(name, ms, rec.code)
        else:
            self._unregister_timer(name)

        return rec.enabled
