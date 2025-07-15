# ui/windows/main_window.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QFrame,
    QVBoxLayout, QHBoxLayout, QStatusBar
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import QIcon, QAction

from ui.widgets.console.console import Console
from ui.windows.alias_editor   import AliasEditorWindow
from ui.windows.timer_editor import TimerEditorWindow
from ui.windows.trigger_editor import TriggerEditorWindow


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()

        # Reference to core App
        self.app = app

        # Window setup
        self.setWindowTitle("Skald MUD Client")
        self.setWindowIcon(QIcon("assets/skald_icon.png"))
        self.setMinimumSize(800, 600)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)

        # Menus and Status Bar
        self._create_menu()
        self._create_status_bar()

        # Central layout
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(3, 0, 3, 0)
        layout.setSpacing(5)
        self.setCentralWidget(central)

        # Splitter: left, center, right
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet("QSplitter::handle { background-color: #444; }")
        layout.addWidget(splitter)

        # Left panel
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_panel.setStyleSheet("background-color: #1e1e1e;")
        splitter.addWidget(self.left_panel)

        # Center panel with Console
        self.center_panel = QFrame()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setStyleSheet("background-color: black;")
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        self.console = Console()
        center_layout.addWidget(self.console)
        splitter.addWidget(self.center_panel)

        # Right panel
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        self.right_panel.setStyleSheet("background-color: #1e1e1e;")
        splitter.addWidget(self.right_panel)

        # Initial sizes
        splitter.setSizes([200, 600, 200])

        # Connect console input
        self.console.commandEntered.connect(self._handle_command)
        QTimer.singleShot(0, self.console.input.setFocus)

    def _create_menu(self):
        menu = self.menuBar()

        client_menu = menu.addMenu("&Client")
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        client_menu.addAction(exit_action)

        scripts_menu = menu.addMenu("&Scripts")

        aliases_action = QAction("Aliases", self)
        aliases_action.triggered.connect(self._open_aliases_window)
        scripts_menu.addAction(aliases_action)

        timers_action = QAction("Timers", self)
        timers_action.triggered.connect(self._open_timers_window)
        scripts_menu.addAction(timers_action)

        triggers_action = QAction("Triggers", self)
        triggers_action.triggered.connect(self._open_triggers_window)
        scripts_menu.addAction(triggers_action)

    def _create_status_bar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    def _handle_command(self, text: str):
        # delegate to App: expands aliases + sends
        self.app.send_to_mud(text)

    def _open_aliases_window(self):
        # Instantiate once, then reuse
        if not hasattr(self, "alias_window"):
            self.alias_window = AliasEditorWindow(
                parent         = self,
                alias_manager  = self.app.alias_manager,
                script_manager = self.app.script_manager
            )
        self.alias_window.show()
        self.alias_window.raise_()
        self.alias_window.activateWindow()

    def _open_timers_window(self):
        if not hasattr(self, "timer_window"):
            self.timer_window = TimerEditorWindow(
                parent          = self,
                timer_manager   = self.app.timer_manager,
                script_manager  = self.app.script_manager
            )
        self.timer_window.show()
        self.timer_window.raise_()
        self.timer_window.activateWindow()

    def _open_triggers_window(self):
        if not hasattr(self, "trigger_window"):
            self.trigger_window = TriggerEditorWindow(
                parent          = self,
                trigger_manager = self.app.trigger_manager,
                script_manager  = self.app.script_manager
            )
        self.trigger_window.show()
        self.trigger_window.raise_()
        self.trigger_window.activateWindow()
