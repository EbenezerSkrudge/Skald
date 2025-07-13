# core/trigger.py

import re
from dataclasses import dataclass, field
from typing import Pattern, Callable

@dataclass(order=True)
class Trigger:
    priority: int                                      # higher → run earlier
    name: str = field(compare=False)
    regex: str = field(compare=False)                  # raw regex string
    pattern: Pattern = field(compare=False)            # compiled regex
    action: Callable[[re.Match], None] = field(compare=False)
    enabled: bool = field(default=True, compare=False)

    def __post_init__(self):
        # Ensure our pattern matches the regex string, if someone only set regex:
        if isinstance(self.regex, str) and not hasattr(self.pattern, 'pattern'):
            self.pattern = re.compile(self.regex)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def toggle(self):
        self.enabled = not self.enabled
