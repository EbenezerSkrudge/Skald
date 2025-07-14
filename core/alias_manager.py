# core/alias_manager.py

import re
from typing import List, Optional

from pony.orm import db_session
from data.models import Script  # Pony entity for aliases


class AliasManager:
    """
    Manages regex‐driven aliases at runtime and persists them in the DB.
    API: create(), update(), delete(), toggle(), get_all(), find(), expand().
    """

    def __init__(self):
        # In‐memory list of (priority, compiled_pattern, template)
        self._aliases: List[tuple[int, re.Pattern, str]] = []
        self._load_all_from_db()

    # ─── Public Reload/Clear ───────────────────────────────────

    def clear_all(self) -> None:
        """
        Remove every alias from in‐memory registry.
        """
        self._aliases.clear()

    def reload(self) -> None:
        """
        Clear then re‐load all enabled aliases from DB.
        """
        self.clear_all()
        self._load_all_from_db()

    # ─── Internal Helpers ───────────────────────────────────────

    @db_session
    def _load_all_from_db(self) -> None:
        """
        Load enabled alias‐category Scripts into memory.
        """
        for rec in Script.select(lambda s: s.category == "alias" and s.enabled):
            try:
                pattern = rec.pattern or ""
                compiled = re.compile(pattern)
            except re.error:
                # Skip invalid regex
                continue
            self._aliases.append((rec.priority, compiled, rec.code))
        # Sort descending so highest priority first
        self._aliases.sort(key=lambda t: -t[0])

    # ─── Expansion ─────────────────────────────────────────────

    def expand(self, line: str, max_depth: int = 5) -> str:
        """
        Try to match & expand an alias. Loops up to max_depth for chained
        expansions. Returns original if no alias fires.
        """
        result = line
        depth = 0

        while depth < max_depth:
            for _, pattern, template in self._aliases:
                m = pattern.match(result)
                if not m:
                    continue

                out = template
                # Replace {1}, {2}, ... with capture groups
                for i, grp in enumerate(m.groups(), start=1):
                    out = out.replace(f"{{{i}}}", grp or "")
                result = out
                break
            else:
                return result

            depth += 1

        return result

    # ─── Persistence & CRUD API ────────────────────────────────

    @db_session
    def get_all(self) -> List[Script]:
        """
        Return all alias Scripts from the DB, ordered by priority.
        """
        return list(
            Script
            .select(lambda s: s.category == "alias")
            .order_by(Script.priority)
        )

    @db_session
    def find(self, name: str) -> Optional[Script]:
        """
        Return the alias Script with this name, or None if not found.
        """
        return Script.select(
            lambda s: s.name == name and s.category == "alias"
        ).first()

    @db_session
    def create(
            self,
            name: str,
            pattern: str,
            template: str,
            priority: int = 0,
            enabled: bool = True
    ) -> Script:
        """
        Persist a new alias in the DB and register it in memory.
        """
        rec = Script(
            name=name,
            category="alias",
            pattern=pattern,
            code=template,
            enabled=enabled,
            priority=priority
        )
        rec.flush()

        # register in-memory
        try:
            compiled = re.compile(pattern)
        except re.error:
            return rec
        self._aliases.append((rec.priority, compiled, rec.code))
        self._aliases.sort(key=lambda t: -t[0])
        return rec

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
        Update an existing alias in DB and in memory.
        old_name allows renaming.
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

        # refresh in-memory list
        self.reload()
        return rec

    @db_session
    def delete(self, name: str) -> None:
        """
        Remove alias from DB and in-memory registry.
        """
        rec = self.find(name)
        if rec:
            rec.delete()
        # remove from memory
        self._aliases = [t for t in self._aliases if t[1].pattern != (rec.pattern or "")]

    @db_session
    def toggle(self, name: str) -> Optional[bool]:
        """
        Flip enabled/disabled in DB and in memory.
        Returns new state or None if not found.
        """
        rec = self.find(name)
        if not rec:
            return None

        rec.enabled = not rec.enabled
        rec.flush()

        # refresh in-memory list
        self.reload()
        return rec.enabled
