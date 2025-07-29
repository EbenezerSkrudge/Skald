# core/system_triggers.py

from core.signals import signals
from core.trigger_manager import TriggerManager


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
