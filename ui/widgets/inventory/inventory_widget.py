# ui/widgets/inventory/inventory_widget.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QComboBox,
    QTextBrowser, QScrollArea, QLabel
)
from PySide6.QtCore import Qt
from enum import Enum

from core.signals import signals
from core.managers.inventory_manager import InventoryItem, Inventory


class SortMode(Enum):
    NAME_ASC      = 1
    NAME_DESC     = 2
    QUANTITY_ASC  = 3
    QUANTITY_DESC = 4


class InventoryWidget(QWidget):
    def __init__(self, inventory_manager, parent=None):
        super().__init__(parent)
        self.inventory_manager = inventory_manager
        self._location_map = {
            "carried": "Carried",
            "wielded": "Equipped",
            "worn":    "Equipped",
        }

        self._text_widgets: dict[str, QTextBrowser] = {}
        self._items_by_tab: dict[str, list[InventoryItem]] = {}
        self._sort_mode = SortMode.NAME_ASC

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.sort_dropdown = QComboBox()
        self.sort_dropdown.addItems([
            "Name (A → Z)",
            "Name (Z → A)",
            "Quantity (Low → High)",
            "Quantity (High → Low)"
        ])
        self.sort_dropdown.currentIndexChanged.connect(self._on_sort_changed)
        layout.addWidget(QLabel("Sort by:"))
        layout.addWidget(self.sort_dropdown)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        for title in ("Carried", "Equipped"):
            self._add_tab(title)

        signals.inventory_updated.connect(self._on_inventory_updated)
        self._on_inventory_updated(self.inventory_manager.get_inventory())

    def _add_tab(self, title: str):
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setStyleSheet("""
            QTextBrowser {
                padding: 6px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        browser.setTextInteractionFlags(Qt.TextSelectableByMouse)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setWidget(browser)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)

        self.tabs.addTab(container, title)
        self._text_widgets[title] = browser
        self._items_by_tab[title] = []

    def _on_inventory_updated(self, inventory: Inventory):
        for title in self._items_by_tab:
            self._items_by_tab[title] = []

        for item in inventory.items:
            tab_title = self._location_map.get(item.category, "Other")
            if tab_title not in self._text_widgets:
                self._add_tab(tab_title)
            self._items_by_tab[tab_title].append(item)

        self._refresh_all_tabs()

    def _on_sort_changed(self, index: int):
        self._sort_mode = [
            SortMode.NAME_ASC,
            SortMode.NAME_DESC,
            SortMode.QUANTITY_ASC,
            SortMode.QUANTITY_DESC
        ][index]
        self._refresh_all_tabs()

    def _refresh_all_tabs(self):
        coin_types  = ["gold", "silver", "bronze", "copper"]
        coin_values = {
            "gold":   16**3,
            "silver": 16**2,
            "bronze": 16,
            "copper": 1
        }

        for title, browser in self._text_widgets.items():
            items        = self._items_by_tab.get(title, [])
            coins, others = [], []

            for item in items:
                if self._is_coin(item, coin_types):
                    coins.append(item)
                else:
                    others.append(item)

            coins_sorted  = sorted(
                coins,
                key=lambda i: -self._coin_value(i, coin_types, coin_values)
            )
            others_sorted = self._sort_items(others, self._sort_mode)

            coin_lines   = [
                self._format_quantity(item.quantity, item.name)
                for item in coins_sorted
            ]

            # FIXED: use plural-aware _coin_value() here
            total_copper = sum(
                self._get_numeric_quantity(item)
                * self._coin_value(item, coin_types, coin_values)
                for item in coins
            )

            remaining = total_copper
            gold      = remaining // coin_values["gold"]
            remaining %= coin_values["gold"]
            silver    = remaining // coin_values["silver"]
            remaining %= coin_values["silver"]
            bronze    = remaining // coin_values["bronze"]
            copper    = remaining % coin_values["bronze"]

            summary = (
                f"<span style='color: gray;' title='1g = 16s = 256b = 4096c'>"
                f"Total: {gold}g {silver}s {bronze}b {copper}c = {total_copper}c"
                f"</span>"
            )

            other_lines = [
                self._format_quantity(item.quantity, item.name)
                for item in others_sorted
            ]

            if coin_lines:
                all_lines = coin_lines + [summary] + other_lines
            else:
                all_lines = other_lines

            browser.setHtml(
                "<br>".join(all_lines)
                if all_lines
                else '<span style="color: gray;">No items</span>'
            )

    def _sort_items(self, items: list[InventoryItem], mode: SortMode):
        def quantity_key(item):
            q = item.quantity.lower()
            if q.isdigit():
                return int(q)
            elif q == "some":
                return 1000
            elif q == "many":
                return 1001
            return -1

        def name_key(item):
            name = item.name.lower()
            if name.startswith("a "):
                name = name[2:]
            elif name.startswith("an "):
                name = name[3:]
            return name

        if mode == SortMode.NAME_ASC:
            return sorted(items, key=name_key)
        if mode == SortMode.NAME_DESC:
            return sorted(items, key=name_key, reverse=True)
        if mode == SortMode.QUANTITY_ASC:
            return sorted(items, key=quantity_key)
        if mode == SortMode.QUANTITY_DESC:
            return sorted(items, key=quantity_key, reverse=True)
        return items

    def _format_quantity(self, quantity: str, name: str) -> str:
        if quantity == "1":
            lowered = name.lower()
            if lowered.startswith("a "):
                name = name[2:]
            elif lowered.startswith("an "):
                name = name[3:]
            padded = quantity.rjust(2).replace(" ", "\u00A0")
            return f"<span>{padded}× {name}</span>"

        if quantity.isdigit():
            padded = quantity.rjust(2).replace(" ", "\u00A0")
            return f"<span>{padded}× {name}</span>"

        return f"<span>{quantity.capitalize()} {name}</span>"

    def _is_coin(self, item: InventoryItem, coin_types: list[str]) -> bool:
        name = item.name.lower().strip()
        return any(
            name == f"{t} coin" or name.endswith(f"{t} coins")
            for t in coin_types
        )

    def _coin_value(
        self,
        item: InventoryItem,
        coin_types: list[str],
        coin_values: dict[str, int]
    ) -> int:
        name = item.name.lower().strip()
        for t in coin_types:
            if name.endswith(f"{t} coin") or name.endswith(f"{t} coins"):
                return coin_values[t]
        return 0

    def _get_numeric_quantity(self, item: InventoryItem) -> int:
        q = item.quantity.lower()
        return int(q) if q.isdigit() else 0