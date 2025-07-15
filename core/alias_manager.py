# core/alias_manager.py

import re
from typing import List, Optional, Callable
from pony.orm import db_session
from core.context import Context
from data.models import Script  # Pony entity for aliases


class AliasManager:
    """
    Manages regex-driven aliases at runtime and persists them in the DB.
    """

    def __init__(self, app):
        self._ctx = Context(app)
        self._aliases: List[tuple[int, re.Pattern, Callable]] = []
        self.reload()

    def clear_all(self) -> None:
        """Clear all in-memory aliases."""
        self._aliases.clear()

    def reload(self) -> None:
        """Clear and reload enabled alias Scripts from the DB."""
        self.clear_all()
        self._load_all_from_db()

    @db_session
    def _load_all_from_db(self) -> None:
        for rec in Script.select(lambda s: s.category == "alias" and s.enabled):
            pattern = rec.pattern or ""
            try:
                compiled = re.compile(pattern)
            except re.error:
                continue

            code_obj = compile(rec.code or "", f"<alias:{rec.name}>", "exec")

            def make_action(code_obj=code_obj):
                def action_fn(match):
                    self._ctx.exec_script(code_obj, match=match)
                return action_fn

            self.register_alias(pattern, make_action(), priority=rec.priority)

    def register_alias(
        self,
        pattern: str,
        action_fn: Callable[[re.Match], None],
        priority: int = 0
    ) -> None:
        """Register one alias in memory, sorted by priority desc."""
        compiled = re.compile(pattern)
        self._aliases.append((priority, compiled, action_fn))
        self._aliases.sort(key=lambda x: -x[0])

    def process(self, line: str) -> bool:
        """
        Called by App.send_to_mud().
        Executes first matching alias action and returns True.
        """
        for _, compiled, fn in self._aliases:
            m = compiled.match(line)
            if m:
                fn(m)
                return True
        return False

    @db_session
    def get_all(self) -> List[Script]:
        return list(
            Script
            .select(lambda s: s.category == "alias")
            .order_by(Script.priority)
        )

    @db_session
    def find(self, name: str) -> Optional[Script]:
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
        rec = Script(
            name     = name,
            category = "alias",
            pattern  = pattern,
            code     = code,
            enabled  = enabled,
            priority = priority
        )
        rec.flush()
        if enabled:
            self.register_alias(pattern,
                                 self._make_action_fn(code),
                                 priority=priority)
        return rec

    @db_session
    def update(
        self,
        old_name: str,
        name: str,
        pattern: str,
        code: str,
        priority: int,
        enabled: bool
    ) -> Optional[Script]:
        rec = self.find(old_name)
        if not rec:
            return None

        rec.name     = name
        rec.pattern  = pattern
        rec.code     = code
        rec.priority = priority
        rec.enabled  = enabled
        rec.flush()

        self.reload()
        return rec

    @db_session
    def delete(self, name: str) -> None:
        rec = self.find(name)
        if rec:
            rec.delete()
        self.reload()

    @db_session
    def toggle(self, name: str) -> Optional[bool]:
        rec = self.find(name)
        if not rec:
            return None

        rec.enabled = not rec.enabled
        rec.flush()

        if rec.enabled:
            # register newly enabled alias
            self.register_alias(
                rec.pattern or "",
                self._make_action_fn(rec.code or ""),
                priority=rec.priority
            )
        else:
            self.reload()

        return rec.enabled

    def _make_action_fn(self, code: str):
        code_obj = compile(code or "", "<alias>", "exec")
        def action_fn(match):
            self._ctx.exec_script(code_obj, match=match)
        return action_fn

