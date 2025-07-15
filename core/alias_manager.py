# core/alias_manager.py

import re
from typing import List, Optional, Callable
from pony.orm import db_session
from core.context import Context
from data.models import Script  # Pony entity for aliases


class AliasManager:
    """
    Manages regex‐driven aliases at runtime and persists them in the DB.
    UI/ScriptManager can call clear_all(), register_alias(), reload(),
    plus full CRUD: create(), update(), delete(), toggle(), get_all(), find().
    """

    def __init__(self, app):
        # Shared Context for alias action callbacks
        self._ctx = Context(app)
        # In-memory list of (priority, compiled_pattern, action_fn)
        self._aliases: List[tuple[int, re.Pattern, Callable]] = []
        # Initialize from DB
        self.reload()

    # ─── Public ───────────────────────────────────

    def clear_all(self) -> None:
        """Clear all in-memory aliases."""
        self._aliases.clear()

    def reload(self) -> None:
        """
        Clear and re-load all enabled alias Scripts from the DB,
        compiling and registering each.
        """
        self.clear_all()
        self._load_all_from_db()

    @db_session
    def update(
            self,
            old_name: str,
            name: str,
            pattern: str,
            template: str,
            priority: int,
            enabled: bool
    ) -> Optional[Script]:
        """
        Update an existing alias Script in the DB and refresh in‐memory.
        old_name lets you rename safely.
        """
        rec = self.find(old_name)
        if not rec:
            return None

        rec.name = name
        rec.pattern = pattern
        rec.code = template
        rec.priority = priority
        rec.enabled = enabled
        rec.flush()

        # rebuild in‐memory list so priorities & enabled flags take effect
        self.reload()
        return rec

    # ─── Internal DB Loader ────────────────────────────────────

    @db_session
    def _load_all_from_db(self) -> None:
        """
        Load all Scripts with category=='alias' and enabled==True,
        compile their code into action_fns, and register them.
        """
        for rec in Script.select(lambda s: s.category == "alias" and s.enabled):
            pattern = rec.pattern or ""
            try:
                compiled = re.compile(pattern)
            except re.error:
                continue  # skip invalid regex

            # Compile the Python code into a code object
            code_obj = compile(rec.code or "", f"<alias:{rec.name}>", "exec")

            # Build an action_fn that execs the code with match & ctx
            def make_action(code_obj=code_obj):
                def action_fn(match):
                    exec(
                        code_obj, {},
                        {
                            "match": match,
                            "ctx": self._ctx,
                            "echo": self._ctx.echo,
                            "send": self._ctx.send,
                        }
                    )

                return action_fn

            action_fn = make_action()
            self.register_alias(pattern, action_fn, rec.priority)

    # ─── In-Memory Registration ───────────────────────────────

    def register_alias(
            self,
            pattern: str,
            action_fn: Callable[[re.Match], None],
            priority: int = 0
    ) -> None:
        """
        Register one alias in memory only.
        pattern: regex string
        action_fn: called with the Match when outgoing text matches
        priority: higher priority runs first
        """
        compiled = re.compile(pattern)
        self._aliases.append((priority, compiled, action_fn))
        # Sort so highest priority first
        self._aliases.sort(key=lambda x: -x[0])

    def remove_alias(self, name: str) -> None:
        """
        Unregister any alias with this name from memory.
        Note: name isn’t stored here, so this is a no-op unless you track names.
        You may instead call reload() after delete().
        """
        # If you need name-based removal, you’ll need to store name in the tuple.
        self.reload()

    # ─── Expansion Logic ──────────────────────────────────────

    def process(self, line: str) -> bool:
        """
        Called by App.send_to_mud(). Iterates aliases by priority:
        first matching alias.executes its Python action and returns True.
        If none match, returns False.
        """
        for _, compiled, fn in self._aliases:
            m = compiled.match(line)
            if m:
                fn(m)
                return True
        return False

    # ─── Persistence & CRUD API ────────────────────────────────

    @db_session
    def get_all(self) -> List[Script]:
        """Return all alias Scripts from the DB, ordered by priority."""
        return list(
            Script
            .select(lambda s: s.category == "alias")
            .order_by(Script.priority)
        )

    @db_session
    def find(self, name: str) -> Optional[Script]:
        """Return the alias Script record with this name, or None."""
        return Script.select(
            lambda s: s.name == name and s.category == "alias"
        ).first()

    @db_session
    def create(
            self,
            name: str,
            pattern: str,
            code: str,
            priority: int = 0,
            enabled: bool = True
    ) -> Script:
        """
        Persist a new alias in the DB and register it in memory.
        code: full Python to exec on match.
        """
        rec = Script(
            name=name,
            category="alias",
            pattern=pattern,
            code=code,
            enabled=enabled,
            priority=priority
        )
        rec.flush()

        # Compile & register immediately
        self.reload()
