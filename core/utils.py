# core/utils.py

from pathlib import Path

REQUIRED_PROFILE_FILES = (
    "settings.yaml",
    "data.sqlite"
)

def is_valid_profile(profile_path: Path) -> bool:
    return all((profile_path / filename).exists() for filename in REQUIRED_PROFILE_FILES)
