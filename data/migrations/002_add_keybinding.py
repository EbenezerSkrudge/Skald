# data/migrations/002_add_keybinding.py

def apply(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS KeyBinding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            command TEXT NOT NULL,
            context TEXT,
            UNIQUE(key, context)
        )
    """)

