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

    @property
    def display_name(self) -> str:
        if self.quantity.isdigit():
            padded = self.quantity.rjust(2).replace(" ", "\u00A0")  # preserve leading space
            return f"{padded}× {self.name}"
        else:
            return f"{self.quantity.capitalize()} {self.name}"


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
                print(f"  [{item.category}] {item.quantity}× {item.name}")

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
            "worn":     r"You are wearing (.+?)\.",
            "carried":  r"You are carrying (.+?)\.",
        }
        items_by_category = {}
        for category, pattern in category_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                combined = ', '.join(matches)
                items_by_category[category] = combined
        return items_by_category

    @staticmethod
    def _extract_quantity(item_text: str) -> tuple[str, str]:
        """
        Extracts quantity from item text.
        Returns (quantity_str, cleaned_name), where quantity_str may be a number or a word like 'many'.
        """
        word_to_number = {
            "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
            "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
            "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
            "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
            "nineteen": "19", "twenty": "20"
        }

        descriptive_words = {"some", "many"}

        item_text = item_text.strip()

        # Match digit-based quantity
        match_digit = re.match(r"(\d+)\s+(.*)", item_text)
        if match_digit:
            qty = match_digit.group(1)
            name = match_digit.group(2).strip()
            return qty, name

        # Match word-based quantity
        match_word = re.match(r"([a-zA-Z\-]+)\s+(.*)", item_text)
        if match_word:
            word = match_word.group(1).lower()
            name = match_word.group(2).strip()

            if word in word_to_number:
                return word_to_number[word], name
            elif word in descriptive_words:
                return word, name

        # Default fallback
        return "1", item_text

    @staticmethod
    def _split_items(raw: str) -> List[str]:
        unified = re.sub(r"\s+and\s+", ", ", raw)
        return [item.strip() for item in unified.split(",") if item.strip()]

    def _parse_inventory_block(self, text: str) -> Inventory:
        normalized = self._normalize_text(text)
        category_blocks = self._extract_category_items(normalized)

        items: List[InventoryItem] = []
        for category, raw_items in category_blocks.items():
            for item_text in self._split_items(raw_items):
                quantity, name = self._extract_quantity(item_text)
                items.append(InventoryItem(
                    name=name,
                    category=category,
                    raw_text=item_text,
                    quantity=quantity
                ))

        return Inventory(items)