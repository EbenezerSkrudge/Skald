# core/script_manager.py

import re
from typing        import Dict, TYPE_CHECKING
from pony.orm      import db_session
from PySide6.QtCore import QTimer
from data.models   import Script
from core.context  import Context

if TYPE_CHECKING:
    from core.app             import App
    from core.trigger_manager import TriggerManager


class ScriptManager:
    """
    Loads all Script records from the DB and wires them into
    triggers, timers, aliases, and event handlers.
    """

    def __init__(self, app: "App", trigger_manager: "TriggerManager"):
        self.app  = app
        self.tm   = trigger_manager
        self.ctx  = Context(app)
        self.timers: Dict[str, QTimer] = {}
        self.load_all_scripts()

    @db_session
    def load_all_scripts(self):
        """
        Read every Script row, compile its code, and register it
        in the right place (trigger_manager, timers, aliases, events).
        """
        # clear old in‐memory triggers
        self.tm.clear_all()

        for rec in Script.select().order_by(Script.category, Script.priority):
            if not rec.enabled:
                continue

            code_obj = compile(rec.code, f"<script:{rec.name}>", "exec")

            if rec.category == "trigger":
                action_fn = self._make_trigger_fn(code_obj)
                self.tm.add_trigger(
                    name     = rec.name,
                    regex    = rec.pattern or "",
                    action   = action_fn,
                    enabled  = True,
                    priority = rec.priority
                )

            elif rec.category == "timer":
                interval = float(rec.pattern or 0)
                self._start_timer(rec.name, code_obj, interval)

            elif rec.category == "alias":
                alias_fn = self._make_alias_fn(code_obj)
                self.app.alias_manager.register_alias(rec.pattern, alias_fn)

            elif rec.category.startswith("on_"):
                event_fn = self._make_event_fn(code_obj)
                self.app.register_event_handler(rec.category, event_fn)

    def _make_trigger_fn(self, code_obj):
        """
        Return a function(match, ctx) that execs code_obj with:
          - match
          - ctx
          - echo = ctx.echo
          - send = ctx.send
        """
        def _fn(match, ctx):
            exec(
                code_obj,
                {},
                {
                    "match": match,
                    "ctx":   ctx,
                    "echo":  ctx.echo,
                    "send":  ctx.send           # <- use ctx.send, not send_to_mud
                }
            )
        return _fn

    def _make_alias_fn(self, code_obj):
        """
        Return a function(arg, ctx) for aliases.
        """
        def _fn(arg, ctx):
            exec(
                code_obj,
                {},
                {
                    "arg":  arg,
                    "ctx":  ctx,
                    "send": ctx.send            # <- same here
                }
            )
        return _fn

    def _make_event_fn(self, code_obj):
        """
        Return a function(*args, ctx) for event handlers.
        """
        def _fn(*args, ctx):
            exec(
                code_obj,
                {},
                {
                    "args": args,
                    "ctx":  ctx
                }
            )
        return _fn

    def _start_timer(self, name: str, code_obj, interval: float):
        """
        Set up a QTimer that execs code_obj every `interval` seconds.
        """
        timer = QTimer(self.app.qt_app)
        timer.setInterval(int(interval * 1000))
        # On timeout, run with ctx + send alias
        timer.timeout.connect(lambda: exec(
            code_obj,
            {},
            {
                "ctx":  self.ctx,
                "send": self.ctx.send       # <- and here
            }
        ))
        timer.start()
        self.timers[name] = timer

    def start_timer(self, name: str, interval: float):
        """
        Public API: restart a named script‐timer at runtime.
        """
        with db_session:
            rec = Script.get(name=name)
            if rec:
                code_obj = compile(rec.code, f"<script:{rec.name}>", "exec")
                self._start_timer(name, code_obj, interval)

    def stop_timer(self, name: str):
        """
        Public API: stop a running timer.
        """
        timer = self.timers.pop(name, None)
        if timer:
            timer.stop()
