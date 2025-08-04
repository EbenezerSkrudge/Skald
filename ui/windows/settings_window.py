from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
)
from pony.orm import db_session, select

from data.models import KeyBinding
from ui.widgets.key_capture_edit import KeyCaptureEdit
from ui.widgets.toast import Toast


class SettingsWindow(QDialog):
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._init_profile_tab()
        self._init_keymap_tab()
        self._init_appearance_tab()
        self._init_advanced_tab()

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _init_profile_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)

        self.username_edit = QLineEdit()
        self.auto_connect_check = QCheckBox("Connect automatically on launch")

        form.addRow("Username:", self.username_edit)
        form.addRow("", self.auto_connect_check)

        self.tabs.addTab(tab, "Profile")

    def _init_keymap_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.keymap_table = QTableWidget()
        self.keymap_table.setColumnCount(4)
        self.keymap_table.setHorizontalHeaderLabels(["Key", "Command", "Context", "Delete"])
        self.keymap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(QLabel("Customize key bindings:"))
        layout.addWidget(self.keymap_table)

        add_btn = QPushButton("Add Binding")
        add_btn.clicked.connect(self._add_keymap_row)
        layout.addWidget(add_btn)

        self.tabs.addTab(tab, "Keymap")
        self._load_keymap_rows()

    @db_session
    def _load_keymap_rows(self):
        self.keymap_table.setRowCount(0)

        # Load user-defined bindings
        user_bindings = {
            (kb.key, kb.context): kb.command
            for kb in select(k for k in KeyBinding)
        }

        # Insert default bindings that haven't been overridden
        for (key, context), command in self.app.keymapper.get_defaults().items():
            if (key, context) not in user_bindings:
                self._insert_keymap_row(key, command, context, is_default=True)

        # Insert user-defined bindings (overrides)
        for (key, context), command in user_bindings.items():
            self._insert_keymap_row(key, command, context, is_default=False)

    def _add_keymap_row(self):
        self._insert_keymap_row("", "", "", is_default=False)

    def _insert_keymap_row(self, key, command, context, is_default=False):
        row = self.keymap_table.rowCount()
        self.keymap_table.insertRow(row)

        key_edit = KeyCaptureEdit()
        key_edit.setText(key)
        cmd_edit = QLineEdit(command)
        ctx_edit = QLineEdit(context or "")

        if is_default:
            for widget in (key_edit, cmd_edit, ctx_edit):
                widget.setStyleSheet("color: gray; font-style: italic;")
                widget.setReadOnly(True)

        self.keymap_table.setCellWidget(row, 0, key_edit)
        self.keymap_table.setCellWidget(row, 1, cmd_edit)
        self.keymap_table.setCellWidget(row, 2, ctx_edit)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self.keymap_table.removeRow(row))
        self.keymap_table.setCellWidget(row, 3, delete_btn)

    def _init_appearance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Appearance settings coming soon..."))

        self.tabs.addTab(tab, "Appearance")

    def _init_advanced_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Advanced settings coming soon..."))

        self.tabs.addTab(tab, "Advanced")

    @db_session
    def _save_settings(self):
        KeyBinding.select().delete(bulk=True)

        for row in range(self.keymap_table.rowCount()):
            key = self.keymap_table.cellWidget(row, 0).text().strip()
            command = self.keymap_table.cellWidget(row, 1).text().strip()
            context = self.keymap_table.cellWidget(row, 2).text().strip() or None

            if not key or not command:
                continue

            # Skip if matches default exactly
            if self.app.keymapper.get_defaults().get((key, context)) == command:
                continue

            KeyBinding(key=key, command=command, context=context)

        self.app.keymapper.reload()
        self.show_toast("Keymap updated", duration=2000)

    def show_toast(self, message, duration=2000):
        toast = Toast(message, duration, parent=self)
        geo = self.geometry()
        x = geo.x() + (geo.width() - toast.width()) // 2
        y = geo.y() + geo.height() - toast.height()
        toast.move(x, y)
        toast.show()
