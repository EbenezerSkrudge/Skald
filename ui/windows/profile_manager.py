# ui/windows/profile_manager.py

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QListWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Signal

from core.config import PROFILE_BASE_PATH, HOST, PORT
from core.utils import is_valid_profile
from core.settings import load_settings, save_settings
from core.db import init_db

from core.connection import MudConnection
from ui.windows.main_window import MainWindow


def remove_path(path: Path):
    """Remove a file or entire directory tree."""
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


class ProfileManager(QWidget):
    profileSelected = Signal(Path)

    def __init__(self, app):
        super().__init__(None)
        self.app = app

        # <editor-fold desc="GUI Elements">
        self.setWindowTitle("Select a Profile")
        self.setMinimumSize(400, 300)

        # ─── Widgets ───────────────────────────
        self.profile_list = QListWidget()
        self.profile_list.itemDoubleClicked.connect(self.select_profile)
        self.profile_list.itemSelectionChanged.connect(self._on_selection_changed)

        self.new_profile_input = QLineEdit()
        self.new_profile_input.setPlaceholderText("Enter new profile name")
        self.new_profile_input.setFocus()

        self.create_button = QPushButton("Create")
        self.select_button = QPushButton("Select")
        self.delete_button = QPushButton("Delete")

        # ─── Signals ───────────────────────────
        self.create_button.clicked.connect(self.create_profile)
        self.select_button.clicked.connect(self.select_profile)
        self.delete_button.clicked.connect(self.delete_profile)

        # Disable until selection
        self.select_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        # ─── Layout ────────────────────────────
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.new_profile_input)
        input_layout.addWidget(self.create_button)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.delete_button)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.profile_list)
        outer.addLayout(input_layout)
        outer.addLayout(button_layout)
        # </editor-fold>

        self.load_profiles()

    # ─── Public API ──────────────────────────────────────────────────────────

    def load_profiles(self):
        self.profile_list.clear()
        PROFILE_BASE_PATH.mkdir(parents=True, exist_ok=True)

        for item in PROFILE_BASE_PATH.iterdir():
            if item.is_dir() and is_valid_profile(item):
                self.profile_list.addItem(item.name)

    def create_profile(self):
        name = self.new_profile_input.text()
        profile_path = self._ensure_profile_dir(name)
        if not profile_path:
            return

        try:
            save_settings(profile_path, {
                "font": "Courier New",
                "font_size": 12,
                "theme": "dark",
            })
            init_db(profile_path)
            self.new_profile_input.clear()
            self.load_profiles()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create profile: {e}")

    def select_profile(self):
        item = self.profile_list.currentItem()
        if not item:
            return

        profile_name = item.text()
        profile_path = PROFILE_BASE_PATH / profile_name

        if not is_valid_profile(profile_path):
            QMessageBox.warning(
                self,
                "Invalid Profile",
                f"The selected folder '{profile_name}' is not a valid profile."
            )
            return

        # Emit the selected profile path and close the manager
        self.profileSelected.emit(profile_path)
        self.close()

    def delete_profile(self):
        item = self.profile_list.currentItem()
        if not item:
            return

        profile_name = item.text()
        profile_path = PROFILE_BASE_PATH / profile_name

        confirm = QMessageBox.question(
            self, "Delete Profile",
            f"Are you sure you want to delete profile '{profile_name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            shutil.rmtree(profile_path)
            self.load_profiles()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete profile: {e}")

    # ─── Internal Helpers ──────────────────────────────────────────────────

    def _ensure_profile_dir(self, name: str) -> Path | None:
        """
        Create or validate a profile directory.
        Returns the Path if OK, or None on error/cancellation.
        """
        name = name.strip()
        if not name:
            return None

        path = PROFILE_BASE_PATH / name
        if not path.exists():
            try:
                path.mkdir(parents=True)
                return path
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create directory: {e}")
                return None

        if path.is_file():
            QMessageBox.warning(
                self, "Invalid",
                f"A file named '{name}' exists and cannot be used."
            )
            return None

        if is_valid_profile(path):
            QMessageBox.warning(self, "Exists", f"Profile '{name}' already exists.")
            return None

        # Directory exists but not a valid profile → confirm wipe
        confirm = QMessageBox.warning(
            self, "Directory Exists",
            f"A directory named '{name}' exists but is not a valid profile.\n\n"
            "Creating this profile will erase all contents.\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return None

        # Wipe & recreate
        try:
            remove_path(path)
            path.mkdir(parents=True)
            return path
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear directory: {e}")
            return None

    def _on_selection_changed(self):
        has = bool(self.profile_list.currentItem())
        self.select_button.setEnabled(has)
        self.delete_button.setEnabled(has)
