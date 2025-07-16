# core/event_bus.py

from collections import defaultdict
from typing import Callable

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def register(self, event: str, handler: Callable):
        self._handlers[event].append(handler)

    def unregister(self, event: str, handler: Callable):
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    def fire(self, event: str, *args, **kwargs):
        for handler in self._handlers[event]:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"[EventBus] Error in '{event}' handler: {e}")

# Singleton instance
bus = EventBus()