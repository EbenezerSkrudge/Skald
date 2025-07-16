# core/system_triggers.py

from core.trigger_manager import TriggerManager
from core.signals import signals

def register_system_triggers(manager: TriggerManager):

    def _on_login(match, ctx):
        signals.on_login.emit()

    manager.add_trigger(
        name="login_alert",
        regex=r"(?i).*\b(?:re)?login from\b.*",
        action=_on_login,
        enabled=True,
        priority=0
    )
