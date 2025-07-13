from pony.orm         import Required, Optional, composite_index
from core.db          import db

class Script(db.Entity):
    """
    Represents user‐defined scripts.
    """
    name     = Required(str, unique=True)
    category = Required(str)
    pattern  = Optional(str)
    code     = Required(str)
    enabled  = Required(bool, default=True)
    priority = Required(int, default=0)

    # Pony will now register this index on the same `db`
    composite_index(category, priority)
