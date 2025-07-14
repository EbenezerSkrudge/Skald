# core/app.py

from pathlib import Path
from typing  import Optional

from PySide6.QtWidgets import QApplication

from core.alias_manager    import AliasManager
from core.connection       import MudConnection
from core.config           import HOST, PORT
from core.db               import init_db
from core.settings         import load_settings
from core.script_manager   import ScriptManager
from core.trigger_manager  import TriggerManager
from core.system_triggers  import register_system_triggers
from ui.windows.profile_manager import ProfileManager
from ui.windows.main_window     import MainWindow


class App:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # ensure singleton init runs only once
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.debug_telnet    = True
        self.qt_app          = QApplication([])
        self.main_window     = None
        self.connection      = MudConnection()
        self.profile_path    = Path()
        self.settings        = {}

        self.script_manager  = None
        self.trigger_manager = None
        self.alias_manager   = None

        # Telnet event hooks
        self.connection.dataReceived.connect(self._on_data)
        self.connection.errorOccurred.connect(self._on_error)
        self.connection.disconnected.connect(self._on_disconnect)
        self.connection.gmcpReceived.connect(self._on_gmcp)
        self.connection.negotiation.connect(self._on_negotiation)

    def start(self):
        # Show profile picker first
        pm = ProfileManager(self)
        pm.profileSelected.connect(self.on_profile_selected)
        pm.show()
        self.qt_app.exec()

    def on_profile_selected(self, profile_path: Path):
        # Persist selection
        self.profile_path = profile_path
        self.settings     = load_settings(profile_path)

        # Init database for this profile
        init_db(profile_path / "data.sqlite")

        # Instantiate managers
        self.alias_manager   = AliasManager()
        self.trigger_manager = TriggerManager(self)
        self.script_manager  = ScriptManager(self, self.trigger_manager)
        register_system_triggers(self.trigger_manager, self.send_to_mud)

        # Show main UI
        if self.main_window is None:
            self.main_window = MainWindow(self)
        self.main_window.showMaximized()
        self.main_window.console.input.setFocus()

        # Connect to MUD
        self.connection.connect_to_host(HOST, PORT)

    def toggle_telnet_debug(self):
        self.debug_telnet = not self.debug_telnet
        state = "ON" if self.debug_telnet else "OFF"
        self.main_window.console.echo_html(
            f"<span style='color:yellow'>Telnet debug {state}</span>"
        )

    def send_to_mud(self, text: str):
        """Expands aliases then sends to the MUD."""
        sock = self.connection.socket
        if sock and sock.isOpen():
            expanded = AliasManager().expand(text)
            self.connection.send(expanded)
        else:
            self.main_window.console.echo_html(
                '<span style="color:orange">NO CONNECTION</span>'
            )

    def send_gmcp(self, package: str, payload: Optional[str] = None):
        """Send GMCP package, optionally logging to console."""
        if self.connection.socket and self.connection.socket.isOpen():
            if self.debug_telnet:
                msg = package if payload is None else f"{package} {payload}"
                self.main_window.console.echo(f"[CLIENT GMCP] {msg}")
            self.connection.send_gmcp(package, payload)
        else:
            self.main_window.console.echo_html(
                '<span style="color:orange">NO CONNECTION</span>'
            )

    # ─── Incoming Data ──────────────────────────────────────────

    def _on_data(self, text: str):
        # Echo raw text and fire triggers
        self.main_window.console.echo(text)
        self.trigger_manager.check_triggers(text)

    def _on_gmcp(self, pkg: str, payload):
        if self.debug_telnet:
            self.main_window.console.echo(f"[SERVER GMCP] {pkg} = {payload}")

    def _on_negotiation(self, cmd_value: int, opt: int):
        from core.telnet import TelnetCmd

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
                return

    def _on_disconnect(self):
        # You might show a "disconnected" banner here
        pass

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