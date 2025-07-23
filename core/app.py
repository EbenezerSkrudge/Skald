# core/app.py

import logging
from pathlib    import Path
from typing     import Optional

import json

from PySide6.QtWidgets import QApplication

from core.alias_manager     import AliasManager
from core.connection        import MudConnection
from core.config            import HOST, PORT
from core.db                import init_db
from core.settings          import load_settings
from core.script_manager    import ScriptManager
from core.signals           import signals
from core.timer_manager     import TimerManager
from core.trigger_manager   import TriggerManager
from core.system_triggers   import register_system_triggers
from ui.keymap import KeyMapper

from ui.windows.profile_manager     import ProfileManager
from ui.windows.main_window         import MainWindow

logging.basicConfig(
    level=logging.WARNING,
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
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.debug_telnet = True
        self.qt_app = QApplication([])

        self.profile_path: Path = Path()
        self.settings = {}

        self.connection = MudConnection()
        self.main_window: Optional[MainWindow] = None

        self.alias_manager      = None
        self.timer_manager      = None
        self.trigger_manager    = None
        self.script_manager     = None

        self.gmcp_data = {}

        self._event_handlers: dict[str, list] = {}

        self._init_connection_events()
        signals.on_login.connect(self._on_login)

        self.keymapper = KeyMapper(self)
        self.keymapper.install()

    def start(self):
        pm = ProfileManager(self)
        pm.profileSelected.connect(self.on_profile_selected)
        pm.show()
        self.qt_app.exec()

    def on_profile_selected(self, profile_path: Path):
        self.profile_path = profile_path
        self.settings = load_settings(profile_path)
        init_db(profile_path / "data.sqlite")

        self._init_managers()
        self._init_main_window()
        self.connection.connect_to_host(HOST, PORT)

    def _init_managers(self):
        self.alias_manager = AliasManager(self)
        self.timer_manager = TimerManager(self)
        self.trigger_manager = TriggerManager(self)
        self.script_manager = ScriptManager(self, self.trigger_manager)
        register_system_triggers(self.trigger_manager)

    def _init_main_window(self):
        if self.main_window is None:
            self.main_window = MainWindow(self)
        self.main_window.showMaximized()
        self.main_window.console.input.setFocus()

    def _init_connection_events(self):
        self.connection.dataReceived.connect(self._on_data)
        self.connection.errorOccurred.connect(self._on_error)
        self.connection.disconnected.connect(self._on_disconnect)
        self.connection.gmcpReceived.connect(self._on_gmcp)
        self.connection.negotiation.connect(self._on_negotiation)

    def _check_connection(self) -> bool:
        return self.connection.socket and self.connection.socket.isOpen()

    def send_to_mud(self, text: str):
        if self._check_connection():
            if not self.alias_manager.process(text):
                self.connection.send(text)
        else:
            self._echo_warning("NO CONNECTION")

    def send_gmcp(self, package: str, payload: Optional[str] = None):
        if self._check_connection():
            self.connection.send_gmcp(package, payload)
        else:
            self._echo_warning("NO CONNECTION")

    def _echo_warning(self, message: str):
        self.main_window.console.echo_html(f'<span style="color:orange">{message}</span>')

    # ——— Script Event API ——————————————————————

    def register_event_handler(self, event_name: str, fn: callable):
        self._event_handlers.setdefault(event_name, []).append(fn)

    def clear_event_handlers(self):
        self._event_handlers.clear()

    def fire_event(self, event_name: str, *args):
        for fn in self._event_handlers.get(event_name, []):
            try:
                fn(*args)
            except Exception as e:
                log.exception(f"Error in event handler '{event_name}': {e}")

    # ─── Incoming Data Handlers ─────────────────────

    def _on_data(self, text: str):
        self.main_window.console.echo(text)
        self.trigger_manager.check_triggers(text)

    def _on_gmcp(self, pkg: str, payload):
        log.info(f"[>GMCP] {pkg} = {payload}")

        try:
            parsed = json.loads(payload)
        except (TypeError, ValueError):
            # not valid JSON? just pass it through
            parsed = payload

        self.gmcp_data[pkg] = parsed

        match pkg:
            case "LID":
                if "type" not in self.gmcp_data["LID"]:
                    self.gmcp_data["LID"]["type"] = 0
                self.fire_event("on_location_update", parsed)

            case "CVD":
                # TODO: add on_vitals_update event handler
                pass

            case "MCD":
                # TODO: add on_message_update event handler
                pass

    def _on_negotiation(self, cmd_value: int, opt: int):
        from core.telnet import TelnetCmd

        if opt == TelnetCmd.ECHO:
            cmd = TelnetCmd(cmd_value)
            inp = self.main_window.console.input
            inp.setMasking(cmd == TelnetCmd.WILL)
        elif opt == TelnetCmd.ATCP2:
            self.connection.socket.write(bytes([TelnetCmd.IAC, TelnetCmd.DO, TelnetCmd.ATCP2]))

    def _on_disconnect(self):
        log.info("Disconnected from MUD.")

    def _on_error(self, msg: str):
        log.error(f"[ERROR] {msg}")

    # TODO: Little bit of cludge code here.  Some bug skips the second element of the list so LIB is in twice to compensate.
    def _on_login(self, *args):
        for stream in ["LIB", "LIB", "CVB", "MCB"]:
            self.connection.send_gmcp(stream)

    @classmethod
    def instance(cls):
        return cls()


def begin():
    App.instance().start()


if __name__ == "__main__":
    begin()