# core/managers/inventory_manager.py

import re
from dataclasses import dataclass
from typing import List, Optional, Union

from core.signals import signals


@dataclass
class InventoryItem:
    name: str
    location: str        # "carried", "worn", "wielded", or container name
    slot: Optional[str]  # e.g. "Right Hand", "Left Finger", "Both Hands"
    equipped: bool
    quantity: int


@dataclass
class Inventory:
    items: List[InventoryItem]
    volume: int
    weight: int


class InventoryManager:
    _PATTERNS = {
        "wielded": r"You are wielding\s+(.+?)\.",
        "worn": r"You are wearing\s+(.+?)\.",
        "carried": r"You are carrying\s+(.+?)\.",
    }

    _MUTE_PATTERN = r"You are (?:wielding|wearing|carrying)"

    _WORD_NUMBERS = {
        "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    _DESCRIPTIVE_QTY = {"some": 1000, "many": 1001}

    def __init__(self, app):
        self.app = app
        self._inventory = Inventory(volume=0, weight=0, items=[])
        signals.on_inventory_information.connect(self.update_inventory)

    def get_inventory(self) -> Inventory:
        return self._inventory

    def update_inventory(self, raw: Union[str, re.Match]) -> None:
        text = raw.group(0) if isinstance(raw, re.Match) else raw
        self._inventory.items = self._parse_inventory_block(text)
        self._inventory.volume = self.app.gmcp_data["CVD"]["volume"]
        self._inventory.weight = self.app.gmcp_data["CVD"]["weight"]
        signals.inventory_updated.emit(self._inventory)

    def refresh_inventory(self, timeout: int = 5000):
        """
        Send a muted command to the MUD to refresh and retrieve inventory data.
        The output will be suppressed in the console.
        """
        self.app.send_to_mud(
            text="inventory",  # MUD command to retrieve inventory data
            mute_pattern=self._MUTE_PATTERN,  # Pattern to suppress console echo
            timeout=timeout  # Timeout for muting the response
        )

    def _parse_inventory_block(self, block: str) -> List[InventoryItem]:
        block = re.sub(r"\s+", " ", block.strip())  # normalize whitespace
        items: List[InventoryItem] = []

        for loc, pattern in self._PATTERNS.items():
            if not (match := re.search(pattern, block, re.IGNORECASE)):
                continue

            blob = match.group(1).strip()
            entries = self._split_entries(blob, loc)

            for entry in entries:
                qty, name = self._extract_quantity(entry)
                name, slot = self._extract_slot(name, loc)
                equipped = loc in ("wielded", "worn")

                items.append(InventoryItem(
                    name=name,
                    location=loc,
                    slot=slot,
                    equipped=equipped,
                    quantity=qty
                ))

        return items

    def _split_entries(self, blob: str, loc: str) -> List[str]:
        """Split blob into inventory entries depending on location."""
        sep = r",\s*" if loc == "wielded" else r",\s*|\s+and\s+"
        return [e.strip() for e in re.split(sep, blob) if e.strip()]

    def _extract_quantity(self, text: str) -> tuple[int, str]:
        if m := re.match(r"^(\d+)\s+(.*)$", text):
            return int(m.group(1)), m.group(2).strip()

        if m := re.match(r"^([A-Za-z\-]+)\s+(.*)$", text):
            word, rest = m.group(1).lower(), m.group(2).strip()
            if word in self._WORD_NUMBERS:
                return self._WORD_NUMBERS[word], rest
            if word in self._DESCRIPTIVE_QTY:
                return self._DESCRIPTIVE_QTY[word], rest

        return 1, text

    def _extract_slot(self, name: str, loc: str) -> tuple[str, Optional[str]]:
        """Extract slot phrase from item name if present."""
        if m := re.match(r"(.+?)\s+(?:at|in|with)\s+your\s+(.+)$", name, re.IGNORECASE):
            base_name = m.group(1).strip()
            raw_slot = m.group(2).strip().lower()
            if loc == "wielded" and " and " in raw_slot:
                return base_name, "Both Hands"
            return base_name, raw_slot.title()
        return name, None
