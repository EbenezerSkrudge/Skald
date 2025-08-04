# core/managers/inventory_manager.py

import re
from dataclasses import dataclass
from typing import List

from core.signals import signals


@dataclass
class InventoryItem:
    name: str
    category: str
    raw_text: str
    quantity: int = 1  # Default to 1


@dataclass
class Inventory:
    items: List[InventoryItem]

    def by_category(self, category: str) -> List[InventoryItem]:
        return [item for item in self.items if item.category == category]

    def all_names(self) -> List[str]:
        return [item.name for item in self.items]


class InventoryManager:
    def __init__(self, debug: bool = False):
        self._current_inventory = Inventory(items=[])
        self.debug = debug
        signals.on_inventory_information.connect(self._handle_inventory_block)

    def _handle_inventory_block(self, match):
        raw_text = match.group(0)
        inventory = self._parse_inventory_block(raw_text)

        if self.debug:
            print("📦 Parsed Inventory:")
            for item in inventory.items:
                print(f"  [{item.category}] {item.name}")

        self._current_inventory = inventory
        signals.inventory_updated.emit(inventory)

    def get_inventory(self) -> Inventory:
        return self._current_inventory
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        return ' '.join(text.strip().split())
    
    @staticmethod
    def _extract_category_items(text: str) -> dict:
        category_patterns = {
            "wielded": r"You are wielding (.+?)\.",
            "worn": r"You are wearing (.+?)\.",
            "carried": r"You are carrying (.+?)\.",
        }
        items_by_category = {}
        for category, pattern in category_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                combined = ', '.join(matches)
                items_by_category[category] = combined
        return items_by_category
    
    @staticmethod
    def _extract_quantity(item_text: str) -> tuple[int, str]:
        """
        Extracts quantity from item text if present.
        Returns (quantity, cleaned_name)
        """
        match = re.match(r"(\d+)\s+(.*)", item_text)
        if match:
            qty = int(match.group(1))
            name = match.group(2).strip()
            return qty, name
        return 1, item_text.strip()

    @staticmethod
    def _split_items(raw: str) -> List[str]:
        unified = re.sub(r"\s+and\s+", ", ", raw)
        return [item.strip() for item in unified.split(",") if item.strip()]

    def _parse_inventory_block(self, text: str) -> Inventory:
        normalized = self._normalize_text(text)
        category_blocks = self._extract_category_items(normalized)

        items = []
        for category, raw_items in category_blocks.items():
            for item_text in self._split_items(raw_items):
                quantity, name = self._extract_quantity(item_text)
                items.append(InventoryItem(
                    name=name,
                    category=category,
                    raw_text=item_text,
                    quantity=quantity
                ))
        print(items)
        return Inventory(items)