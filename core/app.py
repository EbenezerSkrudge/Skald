# core/app.py
import logging
from pathlib import Path
from typing  import Optional

from PySide6.QtWidgets import QApplication

from core.alias_manager     import AliasManager
from core.connection        import MudConnection
from core.config            import HOST, PORT
from core.db                import init_db
from core.settings          import load_settings
from core.script_manager    import ScriptManager
from core.timer_manager     import TimerManager
from core.trigger_manager   import TriggerManager
from core.system_triggers   import register_system_triggers
from core.event_bus         import bus

from ui.windows.profile_manager import ProfileManager
from ui.windows.main_window     import MainWindow

logging.basicConfig(
    level=logging.DEBUG,  # or INFO, WARNING, etc.
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

log = logging.getLogger(__name__)

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
        self.timer_manager   = None
        self.trigger_manager = None
        self.alias_manager   = None

        self._event_handlers: dict[str, list] = {}

        # Telnet event hooks
        self.connection.dataReceived.connect(self._on_data)
        self.connection.errorOccurred.connect(self._on_error)
        self.connection.disconnected.connect(self._on_disconnect)
        self.connection.gmcpReceived.connect(self._on_gmcp)
        self.connection.negotiation.connect(self._on_negotiation)

        # Other events
        bus.register("on_login", self._on_login)

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
        self.alias_manager   = AliasManager(self)
        self.timer_manager   = TimerManager(self)
        self.trigger_manager = TriggerManager(self)
        self.script_manager  = ScriptManager(self, self.trigger_manager)

        register_system_triggers(self.trigger_manager)

        # Show main UI
        if self.main_window is None:
            self.main_window = MainWindow(self)
        self.main_window.showMaximized()
        self.main_window.console.input.setFocus()

        # Connect to MUD
        self.connection.connect_to_host(HOST, PORT)

    def send_to_mud(self, text: str):
        sock = self.connection.socket
        if sock and sock.isOpen():
            # 1) Let aliases run first.  If one matches, it executes code & sends.
            handled = self.alias_manager.process(text)
            if not handled:
                # 2) No alias caught it? Just send raw.
                self.connection.send(text)
        else:
            self.main_window.console.echo_html(
                '<span style="color:orange">NO CONNECTION</span>'
            )

    def send_gmcp(self, package: str, payload: Optional[str] = None):
        """Send GMCP package, optionally logging to console."""
        if self.connection.socket and self.connection.socket.isOpen():
            self.connection.send_gmcp(package, payload)
        else:
            self.main_window.console.echo_html(
                '<span style="color:orange">NO CONNECTION</span>'
            )

    # ——— Event‐handler API ——————————————————————————————————

    def register_event_handler(self, event_name: str, fn: callable) -> None:
        """
        Called by ScriptManager for each Script.category == "on_<something>".
        """
        self._event_handlers.setdefault(event_name, []).append(fn)

    def clear_event_handlers(self) -> None:
        """
        Wipe out all script‐driven event handlers
        before re‐loading scripts.
        """
        self._event_handlers.clear()

    def fire_event(self, event_name: str, *args) -> None:
        """
        Invoke all handlers registered under that name.
        Handlers were created with a captured Context, so just call them.
        """
        for fn in self._event_handlers.get(event_name, []):
            try:
                fn(*args)
            except Exception:
                # you may want to log or echo errors here
                pass

    # ─── Incoming Data ──────────────────────────────────────────

    def _on_data(self, text: str):
        # Echo raw text and fire triggers
        self.main_window.console.echo(text)
        self.trigger_manager.check_triggers(text)

    def _on_gmcp(self, pkg: str, payload):
        logging.info(f"[>GMCP] {pkg} = {payload}")

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
            case TelnetCmd.ATCP2:
                self.connection.socket.write(bytes([TelnetCmd.IAC, TelnetCmd.DO, TelnetCmd.ATCP2]))
            case _:
                return

    def _on_disconnect(self):
        # You might show a "disconnected" banner here
        pass

    def _on_error(self, msg: str):
        logging.info(f"[ERROR] {msg}")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ─── Incoming Data ──────────────────────────────────────────
    def _on_login(self, *args):
        """
        Called once on login.  Sends every queued GMCP package.
        """
        for stream in ["LIB", "CVB", "MCB"]:
            self.connection.send_gmcp(stream)

def begin():
    core_app = App.instance()
    core_app.start()


if __name__ == "__main__":
    begin()