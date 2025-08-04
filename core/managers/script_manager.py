# core/script_manager.py

import re
from typing import TYPE_CHECKING

from pony.orm import db_session

from core.context import Context
from data.models import Script

if TYPE_CHECKING:
    from core.app import App
    from core.managers.trigger_manager import TriggerManager


class ScriptManager:
    """
    Reads every Script row and wires it into:
      - TriggerManager (incoming regexes)
      - AliasManager   (outgoing regexes)
      - TimerManager   (interval scripts)
      - App event hooks
    """

    def __init__(self, app: "App", trigger_manager: "TriggerManager"):
        self.app = app
        self.tm = trigger_manager
        self.ctx = Context(app)

        # On startup, load scripts and timers
        self.load_all_scripts()

    @db_session
    def load_all_scripts(self):
        """
        1) Clear triggers, aliases, events
        2) Delegate timer reloading to TimerManager
        3) Loop all enabled Scripts and register them
        """
        # 1) clear existing
        self.tm.clear_all()
        self.app.alias_manager.clear_all()
        self.app.clear_event_handlers()

        # 2) reload timers in one shot
        self.app.timer_manager.reload()

        # 3) load triggers, aliases, events
        for rec in Script.select().order_by(Script.category, Script.priority):
            if not rec.enabled:
                continue

            code_obj = compile(
                rec.code or "", f"<script:{rec.name}>", "exec"
            )

            if rec.category == "trigger":
                # reuse TriggerManager’s compile & register
                self.tm.compile_and_register(rec)

            elif rec.category == "alias":
                self._register_alias(rec.pattern or "", code_obj, rec.priority)

            elif rec.category.startswith("on_"):
                handler = self._make_event_fn(code_obj)
                self.app.register_event_handler(rec.category, handler)

    def _make_event_fn(self, code_obj):
        def fn(*args):
            exec(
                code_obj, {}, {
                    "args": args,
                    "ctx": self.ctx
                }
            )

        return fn

    def _register_alias(self, pattern: str, code_obj, priority: int):
        try:
            re.compile(pattern)
        except re.error:
            return

        def fn(match):
            exec(
                code_obj, {}, {
                    "match": match,
                    "ctx": self.ctx,
                    "echo": self.ctx.echo,
                    "send": self.ctx.send
                }
            )

        self.app.alias_manager.register_alias(
            pattern, fn, priority=priority
        )
