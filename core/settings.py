# core/settings.py
# Settings are client customisation options (e.g. fonts, colours, etc.).  Essential app variables like the
# server port and address, default file locations, etc. should be set via configs and the .env file.

from pathlib import Path

import yaml


def load_settings(profile_path: Path) -> dict:
    settings_file = profile_path / "settings.yaml"
    if not settings_file.exists():
        return {}
    with open(settings_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_settings(profile_path: Path, settings: dict) -> None:
    settings_file = profile_path / "settings.yaml"
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(settings, f)
