# ui/widgets/inventory/inventory_widget.py

from enum import Enum
from collections import defaultdict
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QComboBox, QTextBrowser,
    QScrollArea, QLabel
)

from core.signals import signals
from core.managers.inventory_manager import InventoryItem, Inventory


class SortMode(Enum):
    NAME_ASC = 1
    NAME_DESC = 2
    QUANTITY_ASC = 3
    QUANTITY_DESC = 4


class InventoryWidget(QWidget):
    def __init__(self, inventory_manager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.inventory_manager = inventory_manager
        self._sort_mode = SortMode.NAME_ASC
        self._text_widgets: dict[str, QTextBrowser] = {}
        self._items_by_tab: dict[str, list[InventoryItem]] = {}

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # Controls layout
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(QLabel("Sort:"))

        self.sort_dropdown = QComboBox()
        self.sort_dropdown.addItems([
            "Name (A → Z)",
            "Name (Z → A)",
            "Quantity (Low → High)",
            "Quantity (High → Low)",
        ])
        self.sort_dropdown.currentIndexChanged.connect(self._on_sort_changed)
        controls.addWidget(self.sort_dropdown)

        self.volume_label = QLabel("Vol: 0%")
        self.weight_label = QLabel("Wt: 0%")
        for lbl in (self.volume_label, self.weight_label):
            lbl.setAlignment(Qt.AlignCenter)
            controls.addWidget(lbl)

        controls.addStretch()
        main_layout.addLayout(controls)

        # Tab container
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Connect inventory updates
        signals.inventory_updated.connect(self._on_inventory_updated)

        # Seed initial view
        self._on_inventory_updated(self.inventory_manager.get_inventory())

    # ---------------- Event handlers ---------------- #

    def _on_sort_changed(self, idx: int) -> None:
        self._sort_mode = list(SortMode)[idx]
        self._refresh_all_tabs()

    def _on_inventory_updated(self, inventory: Inventory) -> None:
        # Group items by tab
        self._items_by_tab.clear()
        for item in inventory.items:
            tab = self._get_tab_for_item(item)
            self._items_by_tab.setdefault(tab, []).append(item)

        # Add missing tabs
        for tab in self._items_by_tab:
            if tab not in self._text_widgets:
                self._add_tab(tab)

        # Refresh displays
        self._refresh_all_tabs()

        # Update encumbrance
        self.volume_label.setText(f"Vol: {inventory.volume}%")
        self.weight_label.setText(f"Wt: {inventory.weight}%")

    # ---------------- Tab & rendering ---------------- #

    def _get_tab_for_item(self, item: InventoryItem) -> str:
        if item.location in ("wielded", "worn"):
            return "Equipped"
        if item.location == "carried":
            return "Carried"
        return item.location.title()

    def _add_tab(self, title: str) -> None:
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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(browser)

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(scroll)

        self.tabs.addTab(container, title)
        self._text_widgets[title] = browser

    def _refresh_all_tabs(self) -> None:
        for tab, browser in self._text_widgets.items():
            items = self._items_by_tab.get(tab, [])
            html = (
                self._render_equipped_tab(items)
                if tab == "Equipped"
                else self._render_standard_tab(items)
            )
            browser.setHtml(html)

    # ---------------- HTML rendering helpers ---------------- #

    def _render_equipped_tab(self, items: list[InventoryItem]) -> str:
        lines: list[str] = []

        # Group wielded
        wielded = defaultdict(list)
        for it in filter(lambda x: x.location == "wielded", items):
            wielded[it.slot or "Right Hand"].append(it)
        for slot in sorted(wielded):
            lines.append(f"<b>Wielded: {slot}</b>")
            lines.extend(i.name for i in wielded[slot])

        # Group worn
        worn = defaultdict(list)
        for it in filter(lambda x: x.location == "worn", items):
            worn[it.slot or "Worn"].append(it)
        for slot in sorted(worn):
            lines.append(f"<b>{slot}</b>")
            lines.extend(i.name for i in worn[slot])

        return "<br>".join(lines) if lines else '<span style="color: gray;">No equipped items</span>'

    def _render_standard_tab(self, items: list[InventoryItem]) -> str:
        items = self._sort_items(items)
        if not items:
            return '<span style="color: gray;">No items</span>'
        return "<br>".join(
            f"{i.quantity}&nbsp;&times;&nbsp;{i.name}" if i.quantity > 1 else i.name
            for i in items
        )

    # ---------------- Sorting ---------------- #

    def _sort_items(self, items: list[InventoryItem]) -> list[InventoryItem]:
        def name_key(i: InventoryItem):
            nm = i.name.lower()
            for prefix in ("a ", "an "):
                if nm.startswith(prefix):
                    return nm[len(prefix):]
            return nm

        if self._sort_mode == SortMode.NAME_ASC:
            return sorted(items, key=name_key)
        if self._sort_mode == SortMode.NAME_DESC:
            return sorted(items, key=name_key, reverse=True)
        if self._sort_mode == SortMode.QUANTITY_ASC:
            return sorted(items, key=lambda i: i.quantity)
        if self._sort_mode == SortMode.QUANTITY_DESC:
            return sorted(items, key=lambda i: i.quantity, reverse=True)
        return items
