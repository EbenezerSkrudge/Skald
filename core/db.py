# core/db.py

from pathlib import Path
from sqlite3 import connect

from pony.orm import Database

db = Database()


def init_db(db_path: Path):
    """
    1) Bind Pony to the SQLite file (create if needed).
    2) Generate mapping once, skipping strict schema checks.
    3) Run raw‐SQL migrations to alter tables.
    """
    # Bind & (if no file) create it
    db.bind(provider="sqlite", filename=str(db_path), create_db=True)

    # Generate ORM mapping, create missing tables, but skip validating existing ones
    db.generate_mapping(create_tables=True, check_tables=False)

    # Now apply ALTER TABLE migrations, which add any new columns
    run_migrations(db_path)


def run_migrations(db_path: Path):
    """
    Runs any scripts in migrations/*.py against the raw SQLite file that have yet to be applied.
    Tracks applied filenames in the Migration table.
    """
    conn = connect(str(db_path))
    cursor = conn.cursor()

    # Lazy‐import so Migration entity exists (mapping done above)
    from pony.orm import db_session, select
    from data.models import Migration

    # Figure out which have already run
    with db_session:
        applied = {m.filename for m in select(m for m in Migration)} # type: ignore

    # Locate and execute each new migration
    migration_dir = Path(__file__).parent.parent / "data/migrations"
    for path in sorted(migration_dir.glob("*.py")):
        if path.name in applied:
            continue

        code = compile(path.read_text(), path.name, "exec")
        scope = {}
        exec(code, scope)
        apply_fn = scope.get("apply")
        if callable(apply_fn):
            print(f"Applying migration: {path.name}")
            apply_fn(cursor)

            # Record it
            from datetime import datetime, timezone
            with db_session:
                Migration(
                    filename=path.name,
                    applied=datetime.now(timezone.utc)
                )

    conn.commit()
    conn.close()
