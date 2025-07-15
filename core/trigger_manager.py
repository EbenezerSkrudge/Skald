import re
from typing       import List, Optional

from pony.orm     import db_session
from core.context import Context
from core.trigger import Trigger as TriggerData
from data.models  import Script    # Pony entity for triggers


class TriggerManager:
    """
    Manages regex-driven triggers at runtime *and* persists them in the DB.
    UI can call create(), update(), delete(), toggle(), get_all(), find(),
    or the simpler create_template_trigger()/remove_template_trigger().
    """

    def __init__(self, app):
        # Shared Context for all callbacks
        self._ctx       = Context(app)
        # In-memory list of compiled triggers
        self._triggers: List[TriggerData] = []
        # Load existing triggers from the DB
        self._load_all_from_db()

    # ─── Public Reload/Clear ───────────────────────────────────

    def clear_all(self) -> None:
        """
        Remove every in-memory trigger.
        ScriptManager.load_all_scripts() uses this before re-adding.
        """
        self._triggers.clear()

    def reload(self) -> None:
        """
        Clear and then load all enabled triggers from the DB.
        """
        self.clear_all()
        self._load_all_from_db()

    # ─── Internal Helpers ───────────────────────────────────────

    @db_session
    def _load_all_from_db(self) -> None:
        """Load enabled trigger-category Scripts into memory."""
        for rec in Script.select(lambda s: s.category == "trigger" and s.enabled):
            self._compile_and_register(rec)

    def _compile_and_register(self, rec: Script) -> None:
        """Compile the Python code for one Script and register its action."""
        code_obj = compile(rec.code or "", f"<trigger:{rec.name}>", "exec")

        def action_fn(match, ctx=self._ctx):
            exec(
                code_obj, {},
                {
                    "match": match,
                    "ctx":   ctx,
                    "echo":  ctx.echo,
                    "send":  ctx.send,
                }
            )

        # Register in memory
        self.add_trigger(
            name     = rec.name,
            regex    = rec.pattern or "",
            action   = action_fn,
            enabled  = rec.enabled,
            priority = rec.priority
        )

    # ─── In-Memory Matching ────────────────────────────────────

    def add_trigger(
        self,
        name: str,
        regex: str,
        action,
        enabled: bool = True,
        priority: int = 0
    ) -> None:
        """
        Compile & register a trigger in memory only.
        To persist, use create() or create_template_trigger().
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

        # Remove any old by name, then insert and sort
        self._triggers = [t for t in self._triggers if t.name != name] + [trig]
        self._triggers.sort()

    def remove_trigger(self, name: str) -> None:
        """Unregister a trigger in memory only."""
        self._triggers = [t for t in self._triggers if t.name != name]

    def check_triggers(self, text: str) -> None:
        """
        On each incoming line, fire the first matching enabled trigger,
        passing (match, Context).
        """
        for trig in self._triggers:
            if not trig.enabled:
                continue
            m = trig.pattern.search(text)
            if m:
                trig.action(m, self._ctx)
                break

    # ─── Persistence & CRUD API ────────────────────────────────

    @db_session
    def get_all(self) -> List[Script]:
        """Return all trigger Scripts, ordered by priority."""
        return list(
            Script
            .select(lambda s: s.category == "trigger")
            .order_by(Script.priority)
        )

    @db_session
    def find(self, name: str) -> Optional[Script]:
        """Find a trigger Script by name, or None."""
        return Script.select(
            lambda s: s.name == name and s.category == "trigger"
        ).first()

    @db_session
    def create(
        self,
        name: str,
        regex: str,
        code: str,
        priority: int = 0,
        enabled: bool = True
    ) -> Script:
        """
        Persist a Python-code trigger and register it in memory.
        Returns the new Script record.
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
        Update a trigger record and re-register in memory.
        old_name lets you rename safely.
        """
        rec = self.find(old_name)
        if not rec:
            return None

        rec.name     = name
        rec.pattern  = regex
        rec.code     = code
        rec.priority = priority
        rec.enabled  = enabled
        rec.flush()

        self.remove_trigger(old_name)
        self._compile_and_register(rec)
        return rec

    @db_session
    def delete(self, name: str) -> None:
        """Delete a trigger from DB and unregister it in memory."""
        rec = self.find(name)
        if rec:
            rec.delete()
        self.remove_trigger(name)

    @db_session
    def toggle(self, name: str) -> Optional[bool]:
        """
        Flip enabled/disabled. Persist the change and update memory.
        Returns new state or None if not found.
        """
        rec = self.find(name)
        if not rec:
            return None

        rec.enabled = not rec.enabled
        rec.flush()

        if rec.enabled:
            self._compile_and_register(rec)
        else:
            self.remove_trigger(name)

        return rec.enabled

    # ─── Template-Trigger Convenience ────────────────────────

    def create_template_trigger(
        self,
        name: str,
        regex: str,
        template: str,
        priority: int = 0,
        enabled: bool = True
    ) -> Script:
        """
        Shorthand: persist a simple {named}-template trigger
        whose action only sends formatted text via ctx.send_to_mud.
        """
        def action_fn(match, ctx=self._ctx):
            out = template.format(**match.groupdict())
            ctx.send_to_mud(out)

        rec = self.create(
            name     = name,
            regex    = regex,
            code     = "",  # not used for template triggers
            priority = priority,
            enabled  = enabled
        )
        self.add_trigger(name, regex, action_fn, enabled, priority)
        return rec

    def remove_template_trigger(self, name: str) -> None:
        """Shorthand to delete a simple template-trigger."""
        self.delete(name)
