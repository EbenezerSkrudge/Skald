# core/trigger_manager.py

import re
from typing import List, Optional

from pony.orm        import db_session
from core.context    import Context
from core.trigger    import Trigger as TriggerData
from data.models     import Script  # Pony entity for scripts


class TriggerManager:
    """
    Manages regex‐driven triggers at runtime *and* persists them in the DB.
    UI can call create(), update(), delete(), toggle(), get_all(), find().
    """

    def __init__(self, app):
        # Single shared context for all callbacks
        self._ctx       = Context(app)
        # In-memory list of compiled triggers
        self._triggers: List[TriggerData] = []
        # Load any existing triggers from the DB
        self._load_all_from_db()

    # ─── Internal Helpers ─────────────────────────────────────

    def _compile_and_register(self, rec: Script) -> None:
        # compile the Python code into a code‐object
        code_obj = compile(rec.code or "", f"<script:{rec.name}>", "exec")

        def action_fn(match, ctx):
            # inject both `ctx` and convenient aliases into the locals
            exec(
                code_obj,
                {},
                {
                    "match": match,
                    "ctx":   ctx,
                    "echo":  ctx.echo,
                    "send":  ctx.send_to_mud,   # or ctx.send
                }
            )

            self.add_trigger(
                name=rec.name,
                regex=rec.pattern or "",
                action=action_fn,
                enabled=rec.enabled,
                priority=rec.priority
            )

    @db_session
    def _load_all_from_db(self):
        for rec in Script.select(lambda s: s.category == "trigger"):
            self._compile_and_register(rec)

    def clear_all(self):
        """
        Remove every in-memory trigger.
        Call this before a full reload so you don’t double-register.
        """
        self._triggers.clear()

    # ─── In-Memory Matching ───────────────────────────────────

    def add_trigger(
        self,
        name: str,
        regex: str,
        action,
        enabled: bool = True,
        priority: int = 0
    ):
        """
        (Re)compile + register a trigger in memory.
        This does *not* touch the database.
        """
        compiled = re.compile(regex)
        trig = TriggerData(
            priority = priority,
            name     = name,
            regex    = regex,
            pattern  = compiled,
            action   = action,
            enabled  = enabled,
        )

        # Replace any old trigger by name, then sort ascending
        self._triggers = [t for t in self._triggers if t.name != name] + [trig]
        self._triggers.sort()

    def remove_trigger(self, name: str):
        """Remove from the in-memory registry only."""
        self._triggers = [t for t in self._triggers if t.name != name]

    def check_triggers(self, text: str):
        """
        Call on each incoming line:
        fire the first matching, enabled trigger,
        passing in both match & our Context.
        """
        for trig in self._triggers:
            if not trig.enabled:
                continue
            m = trig.pattern.search(text)
            if not m:
                continue
            # ALWAYS call with TWO parameters now:
            trig.action(m, self._ctx)
            break


    # ─── Persistence & CRUD API ──────────────────────────────

    @db_session
    def get_all(self) -> List[Script]:
        """
        Return a sorted list of all trigger‐category Script entities.
        UI can iterate these to populate the list.
        """
        return list(Script.select(lambda s: s.category == "trigger")
                           .order_by(Script.priority))

    @db_session
    def find(self, name: str) -> Script | None:
        """
        Return the single trigger‐category Script with this name,
        or None if it doesn’t exist.
        """
        return (
            Script
            .select(lambda s: s.name == name and s.category == "trigger")
            .first()
        )

    @db_session
    def create(
        self,
        name: str,
        regex: str,
        code: str,
        priority: int = 1,
        enabled: bool = True
    ) -> Script:
        """
        Create a new trigger in the DB, then register it in memory.
        Returns the new Pony Script record.
        """
        rec = Script(
            name     = name,
            category = "trigger",
            pattern  = regex,
            code     = code,
            enabled  = enabled,
            priority = priority
        )
        rec.flush()
        self._compile_and_register(rec)
        return rec

    @db_session
    def update(
        self,
        old_name: str,
        name: str,
        regex: str,
        code: str,
        priority: int,
        enabled: bool
    ) -> Optional[Script]:
        """
        Update an existing trigger in the DB and in memory.
        old_name allows renaming.
        """
        rec = self.find(old_name)
        if rec is None:
            return None

        rec.name     = name
        rec.pattern  = regex
        rec.code     = code
        rec.priority = priority
        rec.enabled  = enabled
        rec.flush()

        # re-register under new name & settings
        self.remove_trigger(old_name)
        self._compile_and_register(rec)
        return rec

    @db_session
    def delete(self, name: str) -> None:
        """
        Remove the trigger from both DB and in-memory registry.
        """
        rec = self.find(name)
        if rec:
            rec.delete()
        self.remove_trigger(name)

    @db_session
    def toggle(self, name: str) -> Optional[bool]:
        """
        Flip enabled/disabled in DB and in memory.
        Returns the new enabled state or None if not found.
        """
        rec = self.find(name)
        if rec is None:
            return None

        rec.enabled = not rec.enabled
        rec.flush()

        if rec.enabled:
            self._compile_and_register(rec)
        else:
            self.remove_trigger(name)

        return rec.enabled

