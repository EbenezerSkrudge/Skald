# core/timer_manager.py

from typing import List, Optional, Dict

from PySide6.QtCore import QObject, QTimer
from pony.orm import db_session

from core.context import Context
from data.models import Script


class TimerManager(QObject):
    """
    Manages user‐defined timers: Python code blocks that fire every N ms.
    API mirrors TriggerManager/AliasManager: create(), update(), delete(),
    toggle(), get_all(), find(), plus clear_all()/reload() for in-memory.
    """

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._ctx = Context(app)
        self._timers: Dict[str, QTimer] = {}
        self.reload()

    # ── Public Reload / Clear ──────────────────────────────────

    def clear_all(self) -> None:
        """Stop and delete every QTimer."""
        for timer in self._timers.values():
            timer.stop()
            timer.deleteLater()
        self._timers.clear()

    def reload(self) -> None:
        """Clear then load all enabled 'timer' Scripts from the DB."""
        self.clear_all()
        self._load_all_from_db()

    # ── Internal DB Loader ────────────────────────────────────

    @db_session
    def _load_all_from_db(self) -> None:
        for rec in Script.select(lambda s: s.category == "timer" and s.enabled):
            ms = rec.interval or 0
            if ms > 0:
                self._register_timer(rec.name, ms, rec.code)

    def _register_timer(self, name: str, ms: int, code: str) -> None:
        """
        Create or restart one QTimer for this script.
        """
        # If a timer with this name already exists, stop and remove it
        old_timer = self._timers.pop(name, None)
        if old_timer:
            old_timer.stop()
            old_timer.deleteLater()

        # Compile the user code once
        code_obj = compile(code or "", f"<timer:{name}>", "exec")

        # Build the timeout callback capturing code_obj and the shared Context
        def on_timeout():
            self._ctx.exec_script(code_obj)

        # Create, configure, and start the QTimer
        timer = QTimer(self)
        timer.setInterval(ms)
        timer.timeout.connect(on_timeout)
        timer.start()

        # Store it so we can manage it later
        self._timers[name] = timer

    # ── Persistence & CRUD API ────────────────────────────────

    @db_session
    def get_all(self) -> List[Script]:
        """Return all timer Scripts from the DB, ordered by priority."""
        return list(
            Script
            .select(lambda s: s.category == "timer")
            .order_by(Script.priority)
        )

    @db_session
    def find(self, name: str) -> Optional[Script]:
        """Return the timer Script record with this name, or None."""
        return Script.select(
            lambda s: s.name == name and s.category == "timer"
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
        """
        Persist a new timer in the DB and start it if enabled.
        """
        rec = Script(
            name=name,
            category="timer",
            interval=ms,
            code=code,
            enabled=enabled,
            priority=priority
        )
        rec.flush()

        if enabled and ms > 0:
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
        """
        Update an existing timer Script in the DB and restart it under new settings.
        """
        rec = self.find(old_name)
        if not rec:
            return None

        rec.name = name
        rec.interval = ms
        rec.code = code
        rec.priority = priority
        rec.enabled = enabled
        rec.flush()

        # Unregister old timer slot
        self._unregister_timer(old_name)

        # Register under new name/settings
        if enabled and ms > 0:
            self._register_timer(name, ms, code)

        return rec

    @db_session
    def delete(self, name: str) -> None:
        """
        Remove a timer from the DB and stop its QTimer.
        """
        rec = self.find(name)
        if rec:
            rec.delete()
        self._unregister_timer(name)

    @db_session
    def toggle(self, name: str) -> Optional[bool]:
        """
        Flip enabled/disabled in DB and start/stop its QTimer accordingly.
        """
        rec = self.find(name)
        if not rec:
            return None

        rec.enabled = not rec.enabled
        rec.flush()

        if rec.enabled and rec.interval and rec.interval > 0:
            self._register_timer(name, rec.interval, rec.code)
        else:
            self._unregister_timer(name)

        return rec.enabled

    def _unregister_timer(self, name: str) -> None:
        """
        Stop & delete a single timer by name.
        """
        timer = self._timers.pop(name, None)
        if timer:
            timer.stop()
            timer.deleteLater()
