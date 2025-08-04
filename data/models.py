# data/models.py

from datetime import datetime, timezone

from pony.orm import Required, Optional, composite_index, composite_key

from data.db import db


class Migration(db.Entity):
    """
    Tracks which migration scripts have been applied.
    """
    filename = Required(str, unique=True)
    applied = Required(datetime, default=lambda: datetime.now(timezone.utc))


class Script(db.Entity):
    """
    Represents user‐defined scripts.
    """
    name = Required(str, unique=True)
    category = Required(str)
    pattern = Optional(str)
    interval = Optional(int)
    code = Required(str)
    enabled = Required(bool, default=True)
    priority = Required(int, default=0)

    # Pony will now register this index on the same `db`
    composite_index(category, priority)


class KeyBinding(db.Entity):
    key = Required(str)
    command = Required(str)
    context = Optional(str)

    # Enforce uniqueness on (key, context)
    composite_key(key, context)
