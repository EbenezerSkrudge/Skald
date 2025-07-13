# ui/windows/scripting_window.py

from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QMainWindow,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui    import QStandardItemModel, QStandardItem
from PySide6.QtCore   import Qt, QModelIndex

from ui.widgets.code_editor    import CodeEditor
from core.context              import Context
from core.script_manager       import ScriptManager
from data.models               import Script

from pony.orm import db_session


class ScriptingWindow(QMainWindow):
    """
    A dockable window for browsing, editing, and deleting user scripts.
    Left side: tree view grouped by category (trigger, timer, alias, event).
    Right side: code editor for the Python snippet.
    """

    def __init__(self, app, script_manager: ScriptManager):
        super().__init__()
        self.app     = app
        self.sm      = script_manager
        self.ctx     = Context(app)
        self.current = None  # Holds the currently selected Script record

        self.setWindowTitle("Scripts Editor")
        self._create_widgets()
        self._populate_tree()
        self._connect_signals()

    def _create_widgets(self):
        # Main container and layout
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QVBoxLayout(container)

        # Splitter: left = tree, right = editor
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Tree view for categories & script names
        self.tree  = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Category / Script"])
        self.tree.setModel(self.model)
        splitter.addWidget(self.tree)

        # Code editor with syntax highlighting
        self.editor = CodeEditor()
        splitter.addWidget(self.editor)

        # Save / Delete buttons
        btn_layout   = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn   = QPushButton("Save")
        self.delete_btn = QPushButton("Delete")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        main_layout.addLayout(btn_layout)

        # Disable buttons until a script is selected
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    @db_session
    def _populate_tree(self):
        """
        Load all Script rows from the database, grouped by category,
        and populate the tree view.
        """
        # Clear existing items
        self.model.removeRows(0, self.model.rowCount())

        # Group scripts by category
        groups = {}
        for rec in Script.select().order_by(Script.category, Script.priority):
            groups.setdefault(rec.category, []).append(rec)

        # Build the tree
        for category, scripts in groups.items():
            parent_item = QStandardItem(category.capitalize())
            parent_item.setEditable(False)
            self.model.appendRow(parent_item)

            for rec in scripts:
                child_item = QStandardItem(rec.name)
                child_item.setEditable(False)
                child_item.setData(rec.name)  # store script name
                parent_item.appendRow(child_item)

        self.tree.expandAll()

    def _connect_signals(self):
        self.tree.clicked.connect(self._on_tree_clicked)
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)

    def _on_tree_clicked(self, index: QModelIndex):
        """
        When the user selects a script in the tree,
        load its code into the editor.
        """
        name = index.data()
        rec  = Script.get(name=name)
        if rec:
            self.current = rec
            self.editor.setText(rec.code)
            self.save_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        else:
            self.current = None
            self.editor.setText("")
            self.save_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    @db_session
    def _on_save(self):
        """
        Save the edited code back to the database,
        then reload all scripts and refresh the tree.
        """
        if not self.current:
            return

        new_code = self.editor.text()
        self.current.code = new_code
        self.current.flush()

        # Reload engine with updated scripts
        self.sm.load_all_scripts()
        self._populate_tree()

    @db_session
    def _on_delete(self):
        """
        Delete the selected script from the database,
        reload engine scripts, and clear the editor.
        """
        if not self.current:
            return

        self.current.delete()
        self.current = None

        self.sm.load_all_scripts()
        self._populate_tree()
        self.editor.setText("")
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
