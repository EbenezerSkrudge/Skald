# core/script_manager.py

import re
from typing       import Dict, TYPE_CHECKING
from pony.orm     import db_session
from data.models  import Script
from core.context import Context

if TYPE_CHECKING:
    # Only for type hints; not used at runtime
    from core.app import App

class ScriptManager:
    """
    Loads all Script records from the DB and wires them into
    triggers, timers, aliases, and event handlers.
    """

    def __init__(self, app: "App", trigger_manager):
        # store the App *instance* and managers
        self.app     = app
        self.tm      = trigger_manager
        self.ctx     = Context(app)
        self.timers: Dict[str, any] = {}
        # load all scripts on startup
        self._load_all_scripts()

    @db_session
    def _load_all_scripts(self):
        """
        Read every Script row, compile its code, and register it
        in the right place (trigger_manager, timers, aliases, events).
        """
        for rec in Script.select():
            if not rec.enabled:
                continue

            # compile the user‐provided Python snippet
            code_obj = compile(rec.code, f"<script:{rec.name}>", "exec")

            if rec.category == "trigger":
                self.tm.add_trigger(
                    name     = rec.name,
                    regex    = rec.pattern,
                    action   = self._make_trigger_fn(code_obj),
                    enabled  = True,
                    priority = rec.priority
                )

            elif rec.category == "timer":
                interval = float(rec.pattern or 0)
                self._start_timer(rec.name, code_obj, interval)

            elif rec.category == "alias":
                # assumes you have an alias_manager on app
                self.app.alias_manager.register_alias(
                    rec.pattern,
                    self._make_alias_fn(code_obj)
                )

            elif rec.category.startswith("on_"):
                # e.g. on_connect, on_disconnect
                self.app.register_event_handler(
                    rec.category,
                    self._make_event_fn(code_obj)
                )

    def _make_trigger_fn(self, code_obj):
        def _fn(match):
            exec(code_obj, {}, {"match": match, "ctx": self.ctx})
        return _fn

    def _make_alias_fn(self, code_obj):
        def _fn(arg: str):
            exec(code_obj, {}, {"arg": arg, "ctx": self.ctx})
        return _fn

    def _make_event_fn(self, code_obj):
        def _fn(*args):
            exec(code_obj, {}, {"args": args, "ctx": self.ctx})
        return _fn

    def _start_timer(self, name: str, code_obj, interval: float):
        from PySide6.QtCore import QTimer
        timer = QTimer(self.app.qt_app)
        timer.setInterval(int(interval * 1000))
        timer.timeout.connect(lambda: exec(code_obj, {}, {"ctx": self.ctx}))
        timer.start()
        self.timers[name] = timer

    def start_timer(self, name: str, interval: float):
        """
        Public API for scripts to create new timers at runtime.
        You can look up the Script row again and call _start_timer().
        """
        with db_session:
            rec = Script.get(name=name)
            if rec:
                code_obj = compile(rec.code, f"<script:{rec.name}>", "exec")
                self._start_timer(name, code_obj, interval)

    def stop_timer(self, name: str):
        """
        Public API to stop a running timer.
        """
        timer = self.timers.pop(name, None)
        if timer:
            timer.stop()
