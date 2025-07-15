def apply(conn):
    conn.execute("ALTER TABLE Script ADD COLUMN interval INTEGER")
