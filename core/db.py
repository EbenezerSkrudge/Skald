# core/db.py

from pathlib import Path
from data.models import db

def init_db(profile_path: Path):
    """
    Bind the shared `db` to the profile’s SQLite file
    and generate tables if they don’t exist.

    Safe to call multiple times; only binds once.
    """
    if profile_path is None:
        raise ValueError("init_db() requires a non-None profile_path")

    # Only bind once
    if db.provider is None:
        db_path = profile_path / "data.sqlite"
        db.bind(
            provider   = 'sqlite',
            filename   = str(db_path),
            create_db  = True
        )
        db.generate_mapping(create_tables=True)

    return db
