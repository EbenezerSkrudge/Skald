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


class InventoryManager:
    def __init__(self):
        self._inventory = Inventory(items=[])
        signals.on_inventory_information.connect(self.update_inventory)

    def get_inventory(self) -> Inventory:
        return self._inventory

    def update_inventory(self, raw: Union[str, re.Match]) -> None:
        raw_text = raw.group(0) if isinstance(raw, re.Match) else raw
        items = self._parse_inventory_block(raw_text)
        self._inventory.items = items
        signals.inventory_updated.emit(self._inventory)

    def _parse_inventory_block(self, block: str) -> List[InventoryItem]:
        # collapse all whitespace
        block = re.sub(r"\s+", " ", block.strip())

        patterns = {
            "wielded": r"You are wielding\s+(.+?)\.",
            "worn": r"You are wearing\s+(.+?)\.",
            "carried": r"You are carrying\s+(.+?)\.",
        }

        result: List[InventoryItem] = []

        for loc, pat in patterns.items():
            m = re.search(pat, block, re.IGNORECASE)
            if not m:
                continue

            blob = m.group(1).strip()

            # only split on commas for wielded, keep "and" inside the slot phrase
            if loc == "wielded":
                entries = re.split(r",\s*", blob)
            else:
                entries = re.split(r",\s*|\s+and\s+", blob)

            for entry in entries:
                entry = entry.strip()
                if not entry:
                    continue

                qty, name = self._extract_quantity(entry)

                # extract slot phrases like "with your right hand and left hand"
                slot = None
                slot_match = re.match(
                    r"(.+?)\s+(?:at|in|with)\s+your\s+(.+)$",
                    name,
                    re.IGNORECASE
                )
                if slot_match:
                    base_name = slot_match.group(1).strip()
                    raw_slot = slot_match.group(2).strip().lower()

                    # collapse dual-hand into "Both Hands"
                    if loc == "wielded" and " and " in raw_slot:
                        slot = "Both Hands"
                    else:
                        slot = raw_slot.title()

                    name = base_name

                equipped = (loc == "wielded") or (loc == "worn")

                result.append(InventoryItem(
                    name=name,
                    location=loc,
                    slot=slot,
                    equipped=equipped,
                    quantity=qty
                ))

        return result

    def _extract_quantity(self, text: str) -> tuple[int, str]:
        # numeric prefix
        m = re.match(r"^(\d+)\s+(.*)$", text)
        if m:
            return int(m.group(1)), m.group(2).strip()

        # word-number or descriptive
        word_map = {
            "a":1, "an": 1,
            "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10
        }
        desc_map = {"some": 1000, "many": 1001}

        m2 = re.match(r"^([A-Za-z\-]+)\s+(.*)$", text)
        if m2:
            w, rest = m2.group(1).lower(), m2.group(2).strip()
            if w in word_map:
                return word_map[w], rest
            if w in desc_map:
                return desc_map[w], rest

        # fallback
        return 1, text