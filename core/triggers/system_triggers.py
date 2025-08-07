# core/triggers/system_triggers.py

from core.signals import signals
from core.managers.trigger_manager import TriggerManager


def register_system_triggers(manager: TriggerManager):
    def _on_login(_match, _ctx):
        signals.on_login.emit()

    manager.add_trigger(
        name="login_alert",
        regex=r"(?i).*\b(?:re)?login from\b.*",
        action=_on_login,
        enabled=True,
        priority=0
    )

    def _on_inventory_block(match, _ctx):
        # Emit raw inventory block to be handled by InventoryManager
        signals.on_inventory_information.emit(match)

    manager.add_trigger(
        name="inventory_block",
        regex=(
            r"(?s)^.*?\bYou (?:are wielding|are wearing|are carrying|do not carry anything)\b.*"
        ),
        action=_on_inventory_block,
        enabled=True,
        priority=0
    )
