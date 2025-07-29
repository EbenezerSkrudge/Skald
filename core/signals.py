# core/signals.py

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    on_login = Signal()
    # Add other app-wide signals here as needed


# Singleton instance
signals = AppSignals()
