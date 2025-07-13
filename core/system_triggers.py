# core/system_triggers.py

from typing import Callable
from core.trigger_manager import TriggerManager

def register_system_triggers(
    manager: TriggerManager,
    send_fn: Callable[[str], None]
):
    """
    Register built-in triggers; send_fn is your App.send_to_mud.
    """

    manager.add_trigger(
        name="login_alert",
        regex=r"(?i).*\b(?:re)?login from\b.*",
        action=lambda match, ctx: send_fn("Looks like we logged in"),
        enabled=True,
        priority=0
    )

