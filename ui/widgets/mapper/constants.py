# ui/widgets/mapper/constants.py

# Z-values for rendering order
Z_CONNECTOR     = 0
Z_ROOM_SHAPE    = 1
Z_ROOM_LABEL    = 2
Z_ROOM_ICON     = 3
Z_OVERLAY       = 4

ROOM_SIZE       = 40
GRID_SIZE       = 60

DIRECTIONS = [
    # string symbol        numpad key   direction x    y
    {"text": "southwest",   "num": 1,   "delta": (-1, +1)},
    {"text": "south",       "num": 2,   "delta": ( 0, +1)},
    {"text": "southeast",   "num": 3,   "delta": (+1, +1)},
    {"text": "west",        "num": 4,   "delta": (-1,  0)},
    {"text": "east",        "num": 6,   "delta": (+1,  0)},
    {"text": "northwest",   "num": 7,   "delta": (-1, -1)},
    {"text": "north",       "num": 8,   "delta": ( 0, -1)},
    {"text": "northeast",   "num": 9,   "delta": (+1, -1)},
]

# Pre-computed conversions
TEXT_TO_NUM     = {entry["text"]:   entry["num"]    for entry in DIRECTIONS}
NUM_TO_DELTA    = {entry["num"]:    entry["delta"]  for entry in DIRECTIONS}
TEXT_TO_DELTA   = {entry["text"]:   entry["delta"]  for entry in DIRECTIONS}
DELTA_TO_TEXT   = {entry["delta"]:  entry["text"]   for entry in DIRECTIONS}