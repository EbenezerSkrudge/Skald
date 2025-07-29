# core/context.py

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.app import App


class Context:
    def __init__(self, app: "App"):
        self._app = app
        self.vars = {}

    def exec_script(self, code_obj, **extra_locals):
        """
        Execute `code_obj` in a sandbox with:
          - ctx
          - echo
          - send
        plus whatever you pass in `extra_locals`.
        """
        sandbox = {
            "ctx": self,
            #            "match": match,
            "echo": self.echo,
            "send": self.send,
            "send_gmcp": self.send_gmcp,
            "gmcp": self._app.gmcp_data
        }
        sandbox.update(extra_locals)
        exec(code_obj, {}, sandbox)

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
