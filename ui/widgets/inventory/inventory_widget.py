from enum import Enum
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QComboBox,
    QTextBrowser, QScrollArea, QLabel
)

from core.managers.inventory_manager import InventoryItem, Inventory
from core.signals import signals


class SortMode(Enum):
    NAME_ASC      = 1
    NAME_DESC     = 2
    QUANTITY_ASC  = 3
    QUANTITY_DESC = 4


class InventoryWidget(QWidget):
    def __init__(self, inventory_manager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.inventory_manager = inventory_manager
        self._sort_mode = SortMode.NAME_ASC
        self._text_widgets: dict[str, QTextBrowser] = {}
        self._items_by_tab: dict[str, list[InventoryItem]] = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # Sort selector
        main_layout.addWidget(QLabel("Sort by:"))
        self.sort_dropdown = QComboBox()
        self.sort_dropdown.addItems([
            "Name (A → Z)",
            "Name (Z → A)",
            "Quantity (Low → High)",
            "Quantity (High → Low)",
        ])
        self.sort_dropdown.currentIndexChanged.connect(self._on_sort_changed)
        main_layout.addWidget(self.sort_dropdown)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        signals.inventory_updated.connect(self._on_inventory_updated)
        self._on_inventory_updated(self.inventory_manager.get_inventory())

    def _on_sort_changed(self, idx: int):
        self._sort_mode = list(SortMode)[idx]
        self._refresh_all_tabs()

    def _on_inventory_updated(self, inventory: Inventory):
        # rebuild item lists per tab
        self._items_by_tab.clear()
        for itm in inventory.items:
            tab = self._get_tab_for_item(itm)
            self._items_by_tab.setdefault(tab, []).append(itm)

        # ensure tabs exist
        for tab in self._items_by_tab:
            if tab not in self._text_widgets:
                self._add_tab(tab)

        self._refresh_all_tabs()

    def _get_tab_for_item(self, item: InventoryItem) -> str:
        if item.location in ("wielded", "worn"):
            return "Equipped"
        if item.location == "carried":
            return "Carried"
        # any other container
        return item.location.title()

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(browser)

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

        self.tabs.addTab(container, title)
        self._text_widgets[title] = browser

    def _refresh_all_tabs(self):
        for tab, widget in self._text_widgets.items():
            items = self._items_by_tab.get(tab, [])
            if tab == "Equipped":
                widget.setHtml(self._render_equipped_tab(items))
            else:
                widget.setHtml(self._render_standard_tab(items))

    def _render_equipped_tab(self, items: list[InventoryItem]) -> str:
        # split wielded vs worn
        wielded = [i for i in items if i.location == "wielded"]
        worn    = [i for i in items if i.location == "worn"]

        lines: list[str] = []

        # 1) Wielded groups
        from collections import defaultdict
        wg = defaultdict(list)
        for it in wielded:
            slot = it.slot or "Right Hand"
            wg[slot].append(it)

        for slot in sorted(wg.keys()):
            header = f"Wielded: {slot}"
            lines.append(f"<b>{header}</b>")
            for it in wg[slot]:
                lines.append(it.name)

        # 2) Worn groups by slot
        wg2 = defaultdict(list)
        for it in worn:
            key = it.slot or "Worn"
            wg2[key].append(it)

        for slot in sorted(wg2.keys()):
            # ring slot shows “Left Finger” without “Worn:” prefix
            lines.append(f"<b>{slot}</b>")
            for it in wg2[slot]:
                lines.append(it.name)

        if not lines:
            return '<span style="color: gray;">No equipped items</span>'

        return "<br>".join(lines)

    def _render_standard_tab(self, items: list[InventoryItem]) -> str:
        # sort
        items = self._sort_items(items)
        if not items:
            return '<span style="color: gray;">No items</span>'

        lines: list[str] = []
        for it in items:
            if it.quantity > 1:
                lines.append(f"{it.quantity}&nbsp;&times;&nbsp;{it.name}")
            else:
                lines.append(it.name)

        return "<br>".join(lines)

    def _sort_items(self, items: list[InventoryItem]) -> list[InventoryItem]:
        def name_key(i: InventoryItem):
            nm = i.name.lower()
            for prefix in ("a ", "an "):
                if nm.startswith(prefix):
                    return nm[len(prefix):]
            return nm

        def qty_key(i: InventoryItem):
            return i.quantity

        if self._sort_mode == SortMode.NAME_ASC:
            return sorted(items, key=name_key)
        if self._sort_mode == SortMode.NAME_DESC:
            return sorted(items, key=name_key, reverse=True)
        if self._sort_mode == SortMode.QUANTITY_ASC:
            return sorted(items, key=qty_key)
        if self._sort_mode == SortMode.QUANTITY_DESC:
            return sorted(items, key=qty_key, reverse=True)
        return items