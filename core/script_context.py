# core/script_context.py

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.app import App

class ScriptContext:
    def __init__(self, app: "App"):
        self._app = app

    def send(self, text: str):
        self._app.send_to_mud(text)

    def send_gmcp(self, pkg: str, payload: Optional[str] = None):
        self._app.send_gmcp(pkg, payload)

    def echo(self, msg: str):
        self._app.main_window.console.echo(msg)

    def echo_html(self, html: str):
        self._app.main_window.console.echo_html(html)

    def set_timer(self, name: str, interval: float):
        self._app.script_manager.start_timer(name, interval)

    def clear_timer(self, name: str):
        self._app.script_manager.stop_timer(name)

    # add more helpers (room navigation, UI hooks…) as needed
