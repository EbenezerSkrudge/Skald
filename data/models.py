from pony.orm import Database, Required, Optional, composite_index

# Single shared Database instance
db = Database()

class Script(db.Entity):
    """
    Represents a user-defined script in the MUD client.

    A Script can be a trigger, timer, alias, or event handler.
    It holds the matching pattern (if applicable), the Python code to execute,
    and metadata controlling whether and when it fires.

    Class‐level Index:
      • category + priority — speeds up queries filtering by category
        and ordering by priority (ascending).
    """

    name     = Required(str, unique=True)
    category = Required(str)
    pattern  = Optional(str)
    code     = Required(str)
    enabled  = Required(bool, default=True)
    priority = Required(int, default=0)

    composite_index(category, priority)
