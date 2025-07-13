# ui/windows/main_window.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QFrame, QVBoxLayout,
    QHBoxLayout, QStatusBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QAction

from ui.widgets.console.console import Console
from ui.windows.script_window  import ScriptingWindow

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()

        # Parent app
        self.app = app

        # Window setup
        self.setWindowTitle("Skald MUD Client")
        self.setWindowIcon(QIcon("assets/skald_icon.png"))
        self.setMinimumSize(800, 600)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)

        # Menu bar and status bar
        self._create_menu()
        self._create_status_bar()

        # Central widget with margins
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(3, 0, 3, 0)
        central_layout.setSpacing(5)
        self.setCentralWidget(central)

        # Splitter for left/center/right panels
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet("QSplitter::handle { background-color: #444; }")
        central_layout.addWidget(splitter)

        # — Left panel (25%)
        self.left_panel = QFrame()
        self.left_panel.setFrameShape(QFrame.StyledPanel)
        self.left_panel.setStyleSheet("background-color: #1e1e1e;")
        splitter.addWidget(self.left_panel)

        # — Center panel (50%) with Console
        self.center_panel = QFrame()
        self.center_panel.setFrameShape(QFrame.StyledPanel)
        self.center_panel.setStyleSheet("background-color: black;")
        center_layout = QVBoxLayout(self.center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        self.console = Console()
        center_layout.addWidget(self.console)
        splitter.addWidget(self.center_panel)

        # — Right panel (25%)
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.StyledPanel)
        self.right_panel.setStyleSheet("background-color: #1e1e1e;")
        splitter.addWidget(self.right_panel)

        # Initial splitter proportions (pixels or weights)
        splitter.setSizes([200, 400, 200])

        # Signals
        self.console.commandEntered.connect(self._handle_command)

        QTimer.singleShot(0, self.console.input.setFocus)

    def _create_menu(self):
        menu = self.menuBar()

        # File menu
        file_menu = menu.addMenu("&File")
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        # Tools menu
        tools_menu = menu.addMenu("&Tools")

        # Scripts Editor action
        scripts_action = QAction("Scripts Editor", self)
        scripts_action.triggered.connect(self._open_scripting_window)
        tools_menu.addAction(scripts_action)

    def _create_status_bar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    def _handle_command(self, text: str):
        self.app.send_to_mud(text)

    def _open_scripting_window(self):
        """
        Show the Scripts Editor, creating it if needed.
        """
        if getattr(self, "scripting_window", None) is None:
            # app.script_manager is passed in when MainWindow is constructed
            self.scripting_window = ScriptingWindow(self.app, self.app.script_manager)
        self.scripting_window.show()
        self.scripting_window.raise_()
        self.scripting_window.activateWindow()
