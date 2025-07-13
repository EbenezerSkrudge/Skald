# core/trigger_manager.py

import re
from typing import List, Callable
from core.context import Context
from core.trigger import Trigger as TriggerData


class TriggerManager:
    """
    Manages regex-driven triggers at runtime.
    ScriptManager registers triggers here; TriggerManager
    performs matching, sorting, and invocation.
    """

    def __init__(self, app):
        # Single shared context for all callbacks
        self._ctx = Context(app)
        self._triggers: List[TriggerData] = []

    def add_trigger(
            self,
            name: str,
            regex: str,
            action: Callable[[re.Match, Context], None],
            enabled: bool = True,
            priority: int = 0
    ):
        compiled = re.compile(regex)
        trig = TriggerData(
            priority=priority,
            name=name,
            regex=regex,
            pattern=compiled,
            action=action,
            enabled=enabled,
        )

        # replace any old trigger by name, then sort ascending
        self._triggers = [t for t in self._triggers if t.name != name] + [trig]
        self._triggers.sort()

    def remove_trigger(self, name: str):
        self._triggers = [t for t in self._triggers if t.name != name]

    def check_triggers(self, text: str):
        """
        Call this on every incoming line of text.
        It finds the first enabled trigger whose regex matches
        and invokes its action.
        """
        for trig in self._triggers:
            if not trig.enabled:
                continue
            m = trig.pattern.search(text)
            if m:
                trig.action(m, self._ctx)
                break
