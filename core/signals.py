# core/signals.py

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    on_login = Signal()
    on_inventory_information = Signal(object)
    inventory_updated = Signal(object)
    inventory_added = Signal(list)
    inventory_removed = Signal(list)
    # Add other app-wide signals here as needed


# Singleton instance
signals = AppSignals()
