# core/managers/trigger_manager.py

import re
from typing import List, Optional
from pony.orm import db_session

from core.context import Context
from core.triggers.trigger import Trigger as TriggerData
from data.models import Script


class TriggerManager:
    """
    Manages regex-driven triggers at runtime and persists them in the DB.
    Provides CRUD operations, runtime matching, and template-trigger helpers.
    """

    def __init__(self, app):
        self._ctx = Context(app)
        self._triggers: List[TriggerData] = []
        self.reload()

    # ─── Runtime Control ───────────────────────────────────────

    def clear_all(self) -> None:
        """Remove every in-memory trigger."""
        self._triggers.clear()

    def reload(self) -> None:
        """Clear and then load all enabled triggers from the DB."""
        self.clear_all()
        self._load_all_from_db()

    # ─── Internal Loading / Registration ───────────────────────

    @db_session
    def _load_all_from_db(self) -> None:
        for rec in Script.select(lambda s: s.category == "trigger" and s.enabled):
            self.compile_and_register(rec)

    def compile_and_register(self, rec: Script) -> None:
        code_obj = compile(rec.code or "", f"<trigger:{rec.name}>", "exec")

        def action_fn(match, ctx=self._ctx):
            ctx.exec_script(code_obj, match=match)

        # Pass rec.gag into add_trigger
        self.add_trigger(
            name     = rec.name,
            regex    = rec.pattern or "",
            action   = action_fn,
            enabled  = rec.enabled,
            priority = rec.priority,
            gag      = rec.gag,              # ← wire it through
        )


    # ─── In-Memory Matching ────────────────────────────────────

    def add_trigger(
        self,
        name: str,
        regex: str,
        action,
        enabled: bool = True,
        priority: int = 0,
        gag: bool = False,
    ) -> None:
        compiled = re.compile(regex)
        trig = TriggerData(
            priority=priority,
            name=name,
            regex=regex,
            pattern=compiled,
            action=action,
            enabled=enabled,
            gag=gag,                         # ← store it
        )

        # replace old and re-sort
        self._triggers = [t for t in self._triggers if t.name != name] + [trig]
        self._triggers.sort()


    def remove_trigger(self, name: str) -> None:
        """Unregister a trigger in memory."""
        self._triggers = [t for t in self._triggers if t.name != name]

    def check_triggers(self, text: str) -> bool:
        """
        Return True if the first matching enabled trigger has gag=True.
        Side-effects (action) still fire.
        """
        for trig in self._triggers:
            if not trig.enabled:
                continue

            m = trig.pattern.search(text)
            if not m:
                continue

            # fire the trigger action
            trig.action(m, self._ctx)

            # suppress echo if requested
            return trig.gag

        return False


    # ─── Persistence & CRUD ────────────────────────────────────

    @db_session
    def get_all(self) -> List[Script]:
        return list(Script.select(lambda s: s.category == "trigger")
                          .order_by(Script.priority))

    @db_session
    def find(self, name: str) -> Optional[Script]:
        return Script.select(lambda s: s.name == name and s.category == "trigger").first()

    @db_session
    def create(self, name: str, regex: str, code: str, priority=0, enabled=True) -> Script:
        rec = Script(name=name, category="trigger", pattern=regex,
                     code=code, enabled=enabled, priority=priority)
        rec.flush()
        self.compile_and_register(rec)
        return rec

    @db_session
    def update(self, old_name: str, name: str, regex: str, code: str, priority: int, enabled: bool) -> Optional[Script]:
        if not (rec := self.find(old_name)):
            return None
        rec.set(name=name, pattern=regex, code=code, priority=priority, enabled=enabled)
        rec.flush()
        self.remove_trigger(old_name)
        self.compile_and_register(rec)
        return rec

    @db_session
    def delete(self, name: str) -> None:
        if rec := self.find(name):
            rec.delete()
        self.remove_trigger(name)

    @db_session
    def toggle(self, name: str) -> Optional[bool]:
        if not (rec := self.find(name)):
            return None
        rec.enabled = not rec.enabled
        rec.flush()
        if rec.enabled:
            self.compile_and_register(rec)
        else:
            self.remove_trigger(name)
        return rec.enabled

    # ─── Template Trigger Helpers ──────────────────────────────

    def create_template_trigger(self, name: str, regex: str, template: str, priority=0, enabled=True) -> Script:
        """Persist a template trigger that sends formatted output to the MUD."""

        def action_fn(match, ctx=self._ctx):
            ctx.send(template.format(**match.groupdict()))

        rec = self.create(name, regex, code="", priority=priority, enabled=enabled)
        self.add_trigger(name, regex, action_fn, enabled, priority)
        return rec

    def remove_template_trigger(self, name: str) -> None:
        self.delete(name)
