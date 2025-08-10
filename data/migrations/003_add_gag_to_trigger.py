# data/migrations/003_add_gag_to_triggers.py

def apply(cursor):
    """
    Migration 003: Add a 'gag' column to the Script table so
    triggers can optionally suppress (gag) the matching line.
    Existing records default to gag = False (0).
    """
    cursor.execute("""
        ALTER TABLE Script
        ADD COLUMN gag BOOLEAN NOT NULL DEFAULT 0
    """)
