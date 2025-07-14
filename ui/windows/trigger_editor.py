# ui/windows/trigger_editor.py

from PySide6.QtCore    import Qt, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QToolBar, QToolButton, QListWidget, QLineEdit,
    QSpinBox, QLabel, QMessageBox, QStyle, QListWidgetItem
)

from ui.widgets.toggle_switch import ToggleSwitch  # <-- your custom switch
from ui.widgets.code_editor   import CodeEditor

class TriggerEditorWindow(QMainWindow):
    def __init__(self, parent, trigger_manager, script_manager):
        super().__init__(parent)
        self.setWindowTitle("Trigger Editor")
        self.trigger_manager = trigger_manager
        self.script_manager  = script_manager
        self.current_name    = None

        self._create_widgets()
        self._connect_signals()
        self._populate_list()

    def _create_widgets(self):
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QHBoxLayout(container)

        # ── Left: List of trigger names ───────────────────────
        self.list = QListWidget()
        main_layout.addWidget(self.list, 1)

        # ── Right: toolbar + form + code editor ───────────────
        right_container = QWidget()
        right_layout    = QVBoxLayout(right_container)
        main_layout.addWidget(right_container, 3)

        # ── Toolbar with New / Save / Delete ──────────────────
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(32, 32))
        right_layout.addWidget(self.toolbar)

        style       = self.style()
        new_icon    = style.standardIcon(QStyle.SP_FileDialogNewFolder)
        save_icon   = style.standardIcon(QStyle.SP_DialogSaveButton)
        delete_icon = style.standardIcon(QStyle.SP_TrashIcon)

        self.new_btn    = QToolButton(); self.new_btn.setIcon(new_icon)
        self.save_btn   = QToolButton(); self.save_btn.setIcon(save_icon)
        self.delete_btn = QToolButton(); self.delete_btn.setIcon(delete_icon)

        for btn in (self.new_btn, self.save_btn, self.delete_btn):
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setAutoRaise(True)
            btn.setMinimumSize(40, 40)
            self.toolbar.addWidget(btn)

        # ── Metadata row: Name / Priority / Switch ─────────────
        row1 = QWidget(); r1 = QHBoxLayout(row1)
        r1.setContentsMargins(0, 0, 0, 0)

        r1.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        r1.addWidget(self.name_edit, 1)

        r1.addSpacing(12)
        r1.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setMinimum(1)
        r1.addWidget(self.priority_spin)

        r1.addSpacing(12)
        self.enabled_switch = ToggleSwitch()
        r1.addWidget(QLabel("Enabled:"))
        r1.addWidget(self.enabled_switch)

        right_layout.addWidget(row1)

        # ── Row 2: Pattern ────────────────────────────────────
        row2 = QWidget(); r2 = QHBoxLayout(row2)
        r2.setContentsMargins(0, 0, 0, 0)

        r2.addWidget(QLabel("Pattern:"))
        self.pattern_edit = QLineEdit()
        r2.addWidget(self.pattern_edit, 1)

        right_layout.addWidget(row2)

        # ── Action editor ─────────────────────────────────────
        right_layout.addWidget(QLabel("Action:"))
        self.code_edit = CodeEditor()
        right_layout.addWidget(self.code_edit, 2)

        # Initially disable action buttons
        for w in (self.save_btn, self.delete_btn):
            w.setEnabled(False)
        self.enabled_switch.setEnabled(False)

    def _connect_signals(self):
        self.list.currentTextChanged.connect(self._on_select)
        self.new_btn.clicked.connect(self._on_new)
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        self.enabled_switch.toggled.connect(self._on_toggle_changed)

    def _populate_list(self):
        self.list.clear()
        for rec in self.trigger_manager.get_all():
            item = QListWidgetItem()
            item.setText(f"✅ {rec.name}" if rec.enabled else f"❌ {rec.name}")
            item.setData(Qt.UserRole, rec.name)  # store actual name
            color = QColor("#4caf50") if rec.enabled else QColor("#999")
            item.setForeground(color)
            self.list.addItem(item)

    def _on_select(self, label: str):
        item = self.list.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)
        rec = self.trigger_manager.find(name)
        if not rec:
            return

        self.current_name = name
        self.name_edit.setText(rec.name)
        self.priority_spin.setValue(rec.priority)
        self.pattern_edit.setText(rec.pattern or "")
        self.code_edit.set_text(rec.code or "")
        self.enabled_switch.set_checked(rec.enabled)

        for w in (self.save_btn, self.delete_btn, self.enabled_switch):
            w.setEnabled(True)

    def _on_new(self):
        self.current_name = None
        self.list.clearSelection()
        self.name_edit.clear()
        self.priority_spin.setValue(1)
        self.pattern_edit.clear()
        self.code_edit.clear()
        self.enabled_switch.set_checked(True)

        for w in (self.save_btn, self.delete_btn, self.enabled_switch):
            w.setEnabled(True)
        self.delete_btn.setEnabled(False)

    def _on_save(self):
        name     = self.name_edit.text().strip()
        pattern  = self.pattern_edit.text().strip()
        priority = self.priority_spin.value()
        code     = self.code_edit.text()
        enabled  = self.enabled_switch.is_checked()

        if not name or not pattern:
            QMessageBox.warning(self, "Invalid", "Name and Pattern are required.")
            return

        if self.current_name is None:
            rec = self.trigger_manager.create(
                name     = name,
                regex    = pattern,
                code     = code,
                priority = priority,
                enabled  = enabled
            )
            self.current_name = rec.name
        else:
            self.trigger_manager.update(
                old_name = self.current_name,
                name     = name,
                regex    = pattern,
                code     = code,
                priority = priority,
                enabled  = enabled
            )
            self.current_name = name

        # Reload all scripts (including this one)
        self.script_manager.load_all_scripts()

        self._populate_list()
        items = self.list.findItems(name, Qt.MatchExactly)
        if items:
            self.list.setCurrentItem(items[0])

    def _on_delete(self):
        if not self.current_name:
            return
        self.trigger_manager.delete(self.current_name)
        self.script_manager.load_all_scripts()
        self._populate_list()
        self._on_new()

    def _on_toggle_changed(self, enabled: bool):
        if not self.current_name:
            # No selected trigger — ignore until one is picked or saved
            return

        # Update only the 'enabled' field
        rec = self.trigger_manager.find(self.current_name)
        if rec:
            self.trigger_manager.update(
                old_name=rec.name,
                name=rec.name,
                regex=rec.pattern,
                code=rec.code,
                priority=rec.priority,
                enabled=enabled
            )

            self.script_manager.load_all_scripts()
            self._populate_list()

