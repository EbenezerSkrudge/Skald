# core/system_triggers.py

from typing import Callable
from core.trigger_manager import TriggerManager
from core.event_bus import bus

def register_system_triggers(manager: TriggerManager):

    def _on_login(match, ctx):
        from core.app import App
        ctx.echo("Looks like we logged in")
        bus.fire("on_login")

    manager.add_trigger(
        name="login_alert",
        regex=r"(?i).*\b(?:re)?login from\b.*",
        action=_on_login,
        enabled=True,
        priority=0
    )
