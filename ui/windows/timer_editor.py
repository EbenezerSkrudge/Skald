# ui/windows/timer_editor.py

from PySide6.QtCore    import Qt, QSize
from PySide6.QtGui     import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QFrame,
    QVBoxLayout, QHBoxLayout, QToolBar, QToolButton,
    QListWidget, QLineEdit, QSpinBox, QLabel,
    QMessageBox, QStyle, QListWidgetItem, QStatusBar
)

from ui.widgets.toggle_switch import ToggleSwitch
from ui.widgets.code_editor   import CodeEditor


class TimerEditorWindow(QMainWindow):
    def __init__(self, parent, timer_manager, script_manager):
        super().__init__(parent)
        self.setWindowTitle("Timer Editor")

        self.timer_manager  = timer_manager
        self.script_manager = script_manager
        self.current_name   = None

        self._create_widgets()
        self._connect_signals()
        self._populate_list()

    def _create_widgets(self):
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(3, 0, 3, 0)
        main_layout.setSpacing(5)

        # ── Left: list of timers ──────────────────────────────
        self.list = QListWidget()
        main_layout.addWidget(self.list, 1)

        # ── Right: toolbar + form + code editor ───────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        main_layout.addWidget(right, 3)

        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
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
            btn.setMinimumSize(36, 36)
            self.toolbar.addWidget(btn)

        # Metadata row: Name / Interval / Priority / Enabled
        row1 = QWidget(); r1 = QHBoxLayout(row1)
        r1.setContentsMargins(0, 0, 0, 0)

        r1.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        r1.addWidget(self.name_edit, 1)

        r1.addSpacing(12)
        r1.addWidget(QLabel("Interval (ms):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 3600000)
        r1.addWidget(self.interval_spin)

        r1.addSpacing(12)
        r1.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setMinimum(0)
        r1.addWidget(self.priority_spin)

        r1.addSpacing(12)
        r1.addWidget(QLabel("Enabled:"))
        self.enabled_switch = ToggleSwitch()
        r1.addWidget(self.enabled_switch)

        right_layout.addWidget(row1)

        # Code editor
        right_layout.addWidget(QLabel("Code:"))
        self.code_edit = CodeEditor()
        right_layout.addWidget(self.code_edit, 2)

        # Disable controls until selection or new
        for w in (self.save_btn, self.delete_btn, self.enabled_switch):
            w.setEnabled(False)

    def _connect_signals(self):
        self.list.currentTextChanged.connect(self._on_select)
        self.new_btn.clicked.connect(self._on_new)
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        self.enabled_switch.toggled.connect(self._on_toggle_changed)

    def _populate_list(self):
        self.list.clear()
        for rec in self.timer_manager.get_all():
            prefix = "✅ " if rec.enabled else "❌ "
            item = QListWidgetItem(prefix + rec.name)
            item.setData(Qt.UserRole, rec.name)
            color = Qt.green if rec.enabled else Qt.gray
            item.setForeground(color)
            self.list.addItem(item)

    def _on_select(self, _):
        item = self.list.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)
        rec  = self.timer_manager.find(name)
        if not rec:
            return

        self.current_name = name
        self.name_edit.setText(rec.name)
        self.interval_spin.setValue(rec.interval or 0)
        self.priority_spin.setValue(rec.priority)
        self.code_edit.set_text(rec.code or "")
        self.enabled_switch.set_checked(rec.enabled)

        for w in (self.save_btn, self.delete_btn, self.enabled_switch):
            w.setEnabled(True)

    def _on_new(self):
        self.current_name = None
        self.list.clearSelection()
        self.name_edit.clear()
        self.interval_spin.setValue(1000)
        self.priority_spin.setValue(0)
        self.code_edit.clear()
        self.enabled_switch.set_checked(True)

        for w in (self.save_btn, self.delete_btn, self.enabled_switch):
            w.setEnabled(True)
        self.delete_btn.setEnabled(False)

    def _on_save(self):
        name     = self.name_edit.text().strip()
        ms       = self.interval_spin.value()
        priority = self.priority_spin.value()
        code     = self.code_edit.text()
        enabled  = self.enabled_switch.is_checked()

        if not name or ms <= 0:
            QMessageBox.warning(self, "Invalid", "Name and Interval (>0) are required.")
            return

        if self.current_name is None:
            rec = self.timer_manager.create(
                name     = name,
                ms       = ms,
                code     = code,
                priority = priority,
                enabled  = enabled
            )
            self.current_name = rec.name
        else:
            self.timer_manager.update(
                old_name = self.current_name,
                name     = name,
                ms       = ms,
                code     = code,
                priority = priority,
                enabled  = enabled
            )
            self.current_name = name

        # Refresh all scripts (timers + triggers + aliases)
        self.script_manager.load_all_scripts()
        self._populate_list()

        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == self.current_name:
                self.list.setCurrentItem(item)
                break

    def _on_delete(self):
        if not self.current_name:
            return
        self.timer_manager.delete(self.current_name)
        self.script_manager.load_all_scripts()
        self._populate_list()
        self._on_new()

    def _on_toggle_changed(self, enabled: bool):
        if not self.current_name:
            return

        rec = self.timer_manager.find(self.current_name)
        if rec:
            self.timer_manager.update(
                old_name = rec.name,
                name     = rec.name,
                ms       = rec.interval or 0,
                code     = rec.code,
                priority = rec.priority,
                enabled  = enabled
            )
            self.script_manager.load_all_scripts()
            self._populate_list()
