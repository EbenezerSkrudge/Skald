# ui/windows/settings_window.py

from typing            import Optional
from PySide6.QtCore    import Qt, QEvent
from PySide6.QtGui import QKeySequence, QKeyEvent, QColor, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QLabel, QFormLayout,
    QLineEdit, QCheckBox, QPushButton, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication
)
from pony.orm          import db_session, select, commit

from data.models       import KeyBinding
from ui.widgets.toast  import Toast


class SettingsWindow(QDialog):
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 450)

        # For recording shortcuts in the keymap tab
        self.recording_row: Optional[int] = None

        main_layout = QVBoxLayout(self)
        self.tabs    = QTabWidget()
        main_layout.addWidget(self.tabs)

        self._init_profile_tab()
        self._init_keymap_tab()
        self._init_appearance_tab()
        self._init_advanced_tab()

        # Save / Close buttons
        btn_layout = QHBoxLayout()
        save_btn  = QPushButton("Save")
        close_btn = QPushButton("Close")
        save_btn.clicked.connect(self._save_settings)
        close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

    def _init_profile_tab(self):
        tab  = QWidget()
        form = QFormLayout(tab)

        self.username_edit      = QLineEdit()
        self.auto_connect_check = QCheckBox("Connect automatically on launch")

        form.addRow("Username:", self.username_edit)
        form.addRow("", self.auto_connect_check)

        self.tabs.addTab(tab, "Profile")

    def _init_keymap_tab(self):
        tab    = QWidget()
        layout = QVBoxLayout(tab)

        # Header
        layout.addWidget(QLabel("Customize key bindings below:"))

        # Keymap table
        self.keymap_table = QTableWidget(0, 2, self)
        self.keymap_table.setHorizontalHeaderLabels(["Shortcut", "Command"])
        self.keymap_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.keymap_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        # Double-click in Shortcut column to record
        self.keymap_table.cellDoubleClicked.connect(
            self._on_keycell_double_clicked
        )
        layout.addWidget(self.keymap_table)

        # Hint
        hint = QLabel(
            "Double-click a shortcut cell to record a new shortcut", self
        )
        hint.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(hint)

        # Add / Remove buttons
        mod_layout = QHBoxLayout()
        add_btn    = QPushButton("Add Row")
        del_btn    = QPushButton("Remove Row")
        add_btn.clicked.connect(self._add_keymap_row)
        del_btn.clicked.connect(self._remove_keymap_rows)
        mod_layout.addWidget(add_btn)
        mod_layout.addWidget(del_btn)
        mod_layout.addStretch()
        layout.addLayout(mod_layout)

        self.tabs.addTab(tab, "Keymap")
        self._load_keymap_rows()

    @db_session
    def _load_keymap_rows(self):
        """Populate keymap table from database."""
        self.keymap_table.setRowCount(0)
        for kb in select(k for k in KeyBinding):
            self._insert_keymap_row(kb.key, kb.command)

    def _insert_keymap_row(self, key_str: str = "", cmd_str: str = ""):
        """Insert a row into the keymap table."""
        row = self.keymap_table.rowCount()
        self.keymap_table.insertRow(row)

        # Shortcut display: read-only QLineEdit
        key_edit = QLineEdit(self)
        key_edit.setText(key_str)
        key_edit.setReadOnly(True)
        key_edit.setFocusPolicy(Qt.NoFocus)
        key_edit.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.keymap_table.setCellWidget(row, 0, key_edit)

        # Command editor
        cmd_item = QTableWidgetItem(cmd_str)
        self.keymap_table.setItem(row, 1, cmd_item)

    def _add_keymap_row(self):
        self._insert_keymap_row()

    def _remove_keymap_rows(self):
        rows = sorted(
            {idx.row() for idx in self.keymap_table.selectedIndexes()},
            reverse=True
        )
        for r in rows:
            self.keymap_table.removeRow(r)

    def _on_keycell_double_clicked(self, row: int, column: int):
        """Toggle recording mode when Shortcut cell is double-clicked."""
        if column != 0:
            return

        if self.recording_row is None:
            self._start_recording(row)
        else:
            self._stop_recording()

    def _start_recording(self, row: int):
        """Begin capturing the next key press for the given row."""
        self.recording_row = row
        self.keymap_table.selectRow(row)

        # Highlight the row
        highlight = QColor("#fff8b0")
        for col in range(self.keymap_table.columnCount()):
            widget = self.keymap_table.cellWidget(row, col)
            if isinstance(widget, QLineEdit):
                widget.setStyleSheet(f"background-color: {highlight.name()}")
            else:
                item = self.keymap_table.item(row, col)
                if item:
                    item.setBackground(highlight)

        QApplication.instance().installEventFilter(self)

    def _stop_recording(self):
        """Stop capturing and clear highlight."""
        row = self.recording_row
        if row is None:
            return

        for col in range(self.keymap_table.columnCount()):
            widget = self.keymap_table.cellWidget(row, col)
            if isinstance(widget, QLineEdit):
                widget.setStyleSheet("")
            else:
                item = self.keymap_table.item(row, col)
                if item:
                    item.setBackground(QBrush())

        QApplication.instance().removeEventFilter(self)
        self.recording_row = None

    def eventFilter(self, obj, event):
        """
        While recording, catch one non-modifier KeyPress,
        write it into the cell, and exit recording.
        """
        if (
            self.recording_row is not None
            and isinstance(event, QKeyEvent)
            and event.type() == QEvent.KeyPress
        ):
            if event.isAutoRepeat():
                return True

            key = event.key()
            if key in (
                Qt.Key_Control, Qt.Key_Shift,
                Qt.Key_Alt,     Qt.Key_Meta,
                Qt.Key_Super_L, Qt.Key_Super_R
            ):
                # ignore pure modifiers
                return True

            if key == Qt.Key_Escape:
                self._stop_recording()
                return True

            mods     = event.modifiers().value
            combined = mods | key
            seq_text = QKeySequence(
                combined
            ).toString(QKeySequence.NativeText)

            key_widget: QLineEdit = self.keymap_table.cellWidget(
                self.recording_row, 0
            )
            key_widget.setText(seq_text)

            self._stop_recording()
            return True

        return super().eventFilter(obj, event)

    @db_session
    def _save_settings(self):
        """Save profile and keymap settings to the database."""
        # Profile tab save logic here...
        # e.g. write username/auto_connect to config

        # --- Keymap save ---
        # Clear old bindings
        for kb in select(k for k in KeyBinding):
            kb.delete()

        # Write updated bindings
        for row in range(self.keymap_table.rowCount()):
            key_widget: QLineEdit = self.keymap_table.cellWidget(row, 0)
            cmd_item = self.keymap_table.item(row, 1)
            key_text = key_widget.text().strip()
            cmd_text = cmd_item.text().strip() if cmd_item else ""
            if not key_text or not cmd_text:
                continue

            KeyBinding(key=key_text, command=cmd_text)

        commit()
        self.app.keymap_manager.reload()
        Toast("Settings saved", 2000, parent=self).show()
        self.close()

    def showEvent(self, e):
        super().showEvent(e)
        self.app.keymap_manager.enabled = False

    def closeEvent(self, e):
        self.app.keymap_manager.enabled = True
        super().closeEvent(e)

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
