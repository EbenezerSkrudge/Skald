from pathlib import Path
from pony.orm import Database

db = Database()

def init_db(db_file: Path) -> None:
    """
    Bind Pony to a sqlite file and create all tables.
    """
    # make sure parent folder exists
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # bind & auto‐create the file if needed
    db.bind(
        provider   = 'sqlite',
        filename   = str(db_file),
        create_db  = True
    )

    # actually create tables
    db.generate_mapping(create_tables=True)

