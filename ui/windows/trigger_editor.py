# ui/windows/trigger_editor.py
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow,
    QPushButton, QSpinBox, QSplitter, QTextEdit, QToolBar,
    QVBoxLayout, QWidget, QStyle, QToolButton, QMessageBox
)
from PySide6.QtCore import Qt, QSize


class TriggerEditorWindow(QMainWindow):
    def __init__(
        self,
        parent,
        trigger_manager,
        script_manager
    ):
        super().__init__(parent)
        self.setWindowTitle("Trigger Editor")

        # store both managers
        self.trigger_manager = trigger_manager
        self.script_manager  = script_manager

        self.current_name    = None

        self._create_widgets()
        self._connect_signals()
        self._populate_list()


    def _create_widgets(self):
        # Main container
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QHBoxLayout(container)

        # ─── Left: list of trigger names ──────────────────────
        self.list = QListWidget()
        main_layout.addWidget(self.list, 1)

        # ─── Right: toolbar + form + code editor ─────────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        main_layout.addWidget(right_container, 3)

        # Toolbar with New / Save / Delete / Enable buttons
        self.toolbar = QToolBar()
        # Make all toolbar icons 32×32px
        self.toolbar.setIconSize(QSize(32, 32))
        right_layout.addWidget(self.toolbar)

        style = self.style()

        new_icon = style.standardIcon(QStyle.SP_FileDialogNewFolder)
        save_icon = style.standardIcon(QStyle.SP_DialogSaveButton)
        delete_icon = style.standardIcon(QStyle.SP_TrashIcon)
        enable_icon = style.standardIcon(QStyle.SP_DialogYesButton)
        disable_icon = style.standardIcon(QStyle.SP_DialogNoButton)

        # Create the four QToolButtons
        self.new_btn = QToolButton()
        self.new_btn.setIcon(new_icon)
        self.save_btn = QToolButton()
        self.save_btn.setIcon(save_icon)
        self.delete_btn = QToolButton()
        self.delete_btn.setIcon(delete_icon)
        self.toggle_btn = QToolButton()
        self.toggle_btn.setIcon(enable_icon)

        for btn in (self.new_btn, self.save_btn, self.delete_btn, self.toggle_btn):
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setAutoRaise(True)
            # Enlarge the clickable area to 40×40px
            btn.setIconSize(QSize(32, 32))
            btn.setMinimumSize(40, 40)
            self.toolbar.addWidget(btn)

        # ─── Metadata form ───────────────────────────────────
        # Row 1: Name and Priority
        row1 = QWidget()
        r1 = QHBoxLayout(row1)
        r1.setContentsMargins(0, 0, 0, 0)

        r1.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        r1.addWidget(self.name_edit, 1)

        r1.addSpacing(12)
        r1.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setMinimum(1)
        r1.addWidget(self.priority_spin)

        right_layout.addWidget(row1)

        # Row 2: Pattern
        row2 = QWidget()
        r2 = QHBoxLayout(row2)
        r2.setContentsMargins(0, 0, 0, 0)

        r2.addWidget(QLabel("Pattern:"))
        self.pattern_edit = QLineEdit()
        r2.addWidget(self.pattern_edit, 1)

        right_layout.addWidget(row2)

        # ─── Action editor ────────────────────────────────────
        right_layout.addWidget(QLabel("Action:"))
        self.code_edit = QTextEdit()
        right_layout.addWidget(self.code_edit, 2)

        # Disable Save/Delete/Toggle until a trigger is selected
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.toggle_btn.setEnabled(False)


    def _connect_signals(self):
        self.list.currentTextChanged.connect(self._on_select)
        self.new_btn.clicked.connect(self._on_new)
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        self.toggle_btn.clicked.connect(self._on_toggle)

    def _populate_list(self):
        """Load all trigger names into the list."""
        self.list.clear()
        for trig in self.trigger_manager.get_all():  # you’ll implement this
            self.list.addItem(trig.name)

    def _on_select(self, name: str):
        """When a trigger is selected, load its data into the form."""
        trig = self.trigger_manager.find(name)  # you’ll implement this
        if not trig:
            return

        self.current_name = name
        self.name_edit.setText(trig.name)
        self.pattern_edit.setText(trig.pattern)
        self.priority_spin.setValue(trig.priority)
        self.code_edit.setPlainText(trig.code or "")
        for btn in (self.save_btn, self.delete_btn, self.toggle_btn):
            btn.setEnabled(True)

    def _on_new(self):
        """Clear the form for a brand‐new trigger."""
        self.current_name = None
        self.list.clearSelection()
        self.name_edit.clear()
        self.pattern_edit.clear()
        self.priority_spin.setValue(1)
        self.code_edit.clear()
        self.save_btn.setEnabled(True)
        self.delete_btn.setEnabled(False)
        self.toggle_btn.setEnabled(False)

    def _on_save(self):
        name     = self.name_edit.text().strip()
        pattern  = self.pattern_edit.text().strip()
        priority = self.priority_spin.value()
        code     = self.code_edit.toPlainText()

        # Validate
        if not name or not pattern:
            QMessageBox.warning(self, "Invalid", "Name and Pattern are required.")
            return

        # Create or update in DB + in-memory
        if self.current_name is None:
            rec = self.trigger_manager.create(
                name     = name,
                regex    = pattern,
                code     = code,
                priority = priority,
                enabled  = True
            )
            self.current_name = rec.name
        else:
            # preserve enabled state
            rec = self.trigger_manager.find(self.current_name)
            enabled = rec.enabled if rec else True

            rec = self.trigger_manager.update(
                old_name = self.current_name,
                name     = name,
                regex    = pattern,
                code     = code,
                priority = priority,
                enabled  = enabled
            )
            self.current_name = rec.name

        self.script_manager.load_all_scripts()

        # Refresh the UI list and keep your selection
        self._populate_list()
        matches = self.list.findItems(name, Qt.MatchExactly)
        if matches:
            self.list.setCurrentItem(matches[0])

        self.save_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.toggle_btn.setEnabled(True)

    def _on_delete(self):
        """Delete the current trigger."""
        if not self.current_name:
            return
        self.trigger_manager.delete(self.current_name)
        self._populate_list()
        self._on_new()

    def _on_toggle(self):
        """Enable or disable the current trigger."""
        if not self.current_name:
            return
        self.trigger_manager.toggle(self.current_name)
        # you may update the button text/color to indicate state
