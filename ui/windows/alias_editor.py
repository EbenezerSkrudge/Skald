# ui/windows/alias_editor.py

from PySide6.QtCore    import Qt, QSize
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QToolBar,
    QToolButton, QListWidget, QListWidgetItem, QLabel,
    QLineEdit, QSpinBox, QMessageBox, QStyle
)

from ui.widgets.toggle_switch import ToggleSwitch
from ui.widgets.code_editor   import CodeEditor


class AliasEditorWindow(QMainWindow):
    def __init__(self, parent, alias_manager, script_manager):
        super().__init__(parent)
        self.setWindowTitle("Alias Editor")

        self.alias_manager  = alias_manager
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

        # ── Left: list of aliases ─────────────────────────────
        self.list = QListWidget()
        main_layout.addWidget(self.list, 1)

        # ── Right: toolbar + form + code editor ──────────────
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

        # Form row: Name / Pattern / Priority / Enabled
        form = QWidget()
        f = QHBoxLayout(form)
        f.setContentsMargins(0, 0, 0, 0)

        f.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        f.addWidget(self.name_edit, 1)

        f.addSpacing(12)
        f.addWidget(QLabel("Pattern:"))
        self.pattern_edit = QLineEdit()
        f.addWidget(self.pattern_edit, 1)

        f.addSpacing(12)
        f.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setMinimum(0)
        f.addWidget(self.priority_spin)

        f.addSpacing(12)
        f.addWidget(QLabel("Enabled:"))
        self.enabled_switch = ToggleSwitch()
        f.addWidget(self.enabled_switch)

        right_layout.addWidget(form)

        # Code editor (HERE is where code_edit is defined)
        right_layout.addWidget(QLabel("Code:"))
        self.code_edit = CodeEditor()
        right_layout.addWidget(self.code_edit, 2)

        # Disable buttons until an item is selected or "New"
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
        for rec in self.alias_manager.get_all():
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
        rec  = self.alias_manager.find(name)
        if not rec:
            return

        self.current_name = name
        self.name_edit.setText(rec.name)
        self.pattern_edit.setText(rec.pattern or "")
        self.priority_spin.setValue(rec.priority)
        self.code_edit.set_text(rec.code or "")
        self.enabled_switch.set_checked(rec.enabled)

        for w in (self.save_btn, self.delete_btn, self.enabled_switch):
            w.setEnabled(True)

    def _on_new(self):
        self.current_name = None
        self.list.clearSelection()
        self.name_edit.clear()
        self.pattern_edit.clear()
        self.priority_spin.setValue(0)
        self.code_edit.clear()
        self.enabled_switch.set_checked(True)

        for w in (self.save_btn, self.delete_btn, self.enabled_switch):
            w.setEnabled(True)
        self.delete_btn.setEnabled(False)

    def _on_save(self):
        name     = self.name_edit.text().strip()
        pattern  = self.pattern_edit.text()
        code     = self.code_edit.text()
        priority = self.priority_spin.value()
        enabled  = self.enabled_switch.is_checked()

        if not name:
            QMessageBox.warning(self, "Invalid", "Name is required.")
            return

        if self.current_name is None:
            rec = self.alias_manager.create(
                name     = name,
                pattern  = pattern,
                code     = code,
                priority = priority,
                enabled  = enabled
            )
            self.current_name = rec.name
        else:
            self.alias_manager.update(
                old_name = self.current_name,
                name     = name,
                pattern  = pattern,
                code     = code,
                priority = priority,
                enabled  = enabled
            )
            self.current_name = name

        self.script_manager.load_all_scripts()
        self._populate_list()

        # Reselect the saved item
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == self.current_name:
                self.list.setCurrentItem(item)
                break

    def _on_delete(self):
        if not self.current_name:
            return
        self.alias_manager.delete(self.current_name)
        self.script_manager.load_all_scripts()
        self._populate_list()
        self._on_new()

    def _on_toggle_changed(self, enabled: bool):
        if not self.current_name:
            return
        self.alias_manager.toggle(self.current_name)
        self.script_manager.load_all_scripts()
        self._populate_list()
