from pony.orm import Database, Required, Optional

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

    _table_   = "script"
    _indexes_ = [("category", "priority")]

    name     = Required(str, unique=True)
    category = Required(str)    # Script type: "trigger", "timer", "alias", "event", etc.
    pattern  = Optional(str)    # Matching criterion (string, regex, time interval, event etc.)
    code     = Required(str)    # Raw Python source code that will be exec()’d when the script fires
    enabled  = Required(bool, default=True)
    priority = Required(int, default=0)     # Execution ordering within the same category
