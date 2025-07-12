# core/app.py

from pathlib import Path
from typing  import Optional

from PySide6.QtWidgets import QApplication

from ui.windows.profile_manager import ProfileManager
from ui.windows.main_window     import MainWindow

from core.connection import MudConnection
from core.settings   import load_settings
from core.db         import init_db
from core.config     import HOST, PORT
from core.telnet     import TelnetCmd

from core.script_manager  import ScriptManager
from core.trigger_manager import TriggerManager

from core.system_triggers    import register_system_triggers


class App:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.debug_telnet = True
        self.qt_app       = QApplication([])
        self.main_window  = None
        self.connection   = MudConnection()
        self.profile_path = Path()
        self.settings     = {}

        # Telnet hooks
        self.connection.dataReceived.connect(self._on_data)
        self.connection.errorOccurred.connect(self._on_error)
        self.connection.disconnected.connect(self._on_disconnect)
        self.connection.gmcpReceived.connect(self._on_gmcp)
        self.connection.negotiation.connect(self._on_negotiation)

        # Initialize DB & load triggers
        init_db(self.profile_path)

        # Managers
        self.trigger_manager = TriggerManager(self.send_to_mud)
        self.script_manager = ScriptManager(self, self.trigger_manager)

        register_system_triggers(self.trigger_manager, app=self.send_to_mud)

    def start(self):
        pm = ProfileManager(self)
        pm.profileSelected.connect(self.on_profile_selected)
        pm.show()
        self.qt_app.exec()

    def on_profile_selected(self, profile_path: Path):
        self.profile_path = profile_path
        self.settings     = load_settings(profile_path)
        init_db(profile_path)

        if self.main_window is None:
            self.main_window = MainWindow(self)
        self.main_window.showMaximized()
        self.main_window.console.input.setFocus()

        self.connection.connect_to_host(HOST, PORT)

    def toggle_telnet_debug(self):
        self.debug_telnet = not self.debug_telnet
        state = "ON" if self.debug_telnet else "OFF"
        self.main_window.console.echo_html(
            f"<span style='color:yellow'>Telnet debug {state}</span>"
        )

    def send_to_mud(self, text: str):
        sock = self.connection.socket
        if sock and sock.isOpen():
            self.connection.send(text)
        else:
            self.main_window.console.echo_html(
                '<span style="color:orange">NO CONNECTION</span>'
            )

    def send_gmcp(self, package: str, payload: Optional[str] = None):
        if self.connection.socket.isOpen():
            if self.debug_telnet:
                txt = package if payload is None else f"{package} {payload}"
                self.main_window.console.echo(f"[CLIENT GMCP] {txt}")
            self.connection.send_gmcp(package, payload)
        else:
            self.main_window.console.echo_html(
                '<span style="color:orange">NO CONNECTION</span>'
            )

    # ─── Trigger methods ──────────────────────────────────────────

    def add_trigger(
        self,
        name: str,
        regex: str,
        action_template: str,
        enabled: bool = True,
        priority: int = 0
    ):
        """
        Delegate to TriggerManager; it will persist and register.
        """
        # build the callable that will run when the regex matches
        def action_fn(match):
            self.send_to_mud(action_template.format(**match.groupdict()))

        self.trigger_manager.add_trigger(
            name             = name,
            regex            = regex,
            action_template  = action_template,
            action           = action_fn,
            enabled          = enabled,
            priority         = priority,
            persist          = True
        )

    def remove_trigger(self, name: str):
        """
        Delegate removal to TriggerManager (also deletes from DB).
        """
        self.trigger_manager.remove_trigger(name)

    # ─── Internal slots ──────────────────────────────────────────

    def _on_data(self, text: str):
        self.main_window.console.echo(text)
        self.trigger_manager.check_triggers(text)

    def _on_disconnect(self):
        pass

    def _on_gmcp(self, pkg: str, payload):
        if self.debug_telnet:
            self.main_window.console.echo(f"[SERVER GMCP] {pkg} = {payload}")

    def _on_negotiation(self, cmd_value: int, opt: int):
        match opt:
            case TelnetCmd.ECHO:
                cmd = TelnetCmd(cmd_value)
                inp = self.main_window.console.input

                match cmd:
                    case TelnetCmd.WILL:
                        inp.setMasking(True)
                    case TelnetCmd.WONT:
                        inp.setMasking(False)
                    case _:
                        pass
            case _:
                return

    def _on_error(self, msg: str):
        self.main_window.console.echo(f"[ERROR] {msg}")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def begin():
    core_app = App.instance()
    core_app.start()


if __name__ == "__main__":
    begin()