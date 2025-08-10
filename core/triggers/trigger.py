# core/trigger.py

import re
from dataclasses import dataclass
from typing import Callable, Pattern

from core.context import Context

@dataclass
class Trigger:
    """
    In‐memory trigger descriptor.
    action(match, ctx) is called when pattern.search(text) succeeds.
    """

    def __init__(
            self,
            priority: int,
            name: str,
            regex: str,
            pattern: Pattern[str],
            action: Callable[[re.Match[str], Context], None],
            enabled: bool,
            gag: bool
    ):
        self.priority = priority
        self.name = name
        self.regex = regex
        self.pattern = pattern
        # Now properly typed to accept (match, ctx)
        self.action: Callable[[re.Match[str], Context], None] = action
        self.enabled = enabled
        self.gag = gag

    def __lt__(self, other: "Trigger") -> bool:
        return self.priority < other.priority
