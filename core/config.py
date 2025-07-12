# core/config.py
# Configures core app behaviours via the .env file.  These rarely need changing and aren't optional or
# freely customisable.  Client customisation should be done via settings.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROFILE_BASE_PATH               =  Path(os.getenv("PROFILE_BASE_PATH",           "~/Skald")).expanduser()
MAX_COMPLETION_LEXICON_SIZE     =   int(os.getenv("MAX_COMPLETION_LEXICON_SIZE",      1000))
COMPLETION_POPUP_MAX_ROWS       =   int(os.getenv("MAX_COMPLETION_LEXICON_SIZE",         5))
FREEZE_PANE_MIN_HEIGHT          =   int(os.getenv("FREEZE_PANE_MIN_HEIGHT",             80))

HOST                            =       os.getenv("HOST",                        "geas.de")
PORT                            =   int(os.getenv("PORT",                             3334))
TIMEOUT                         = float(os.getenv("TIMEOUT",                            10))
