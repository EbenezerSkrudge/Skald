# game/terrain.py

# Map GMCP “type” codes to (name, color‐hex)
TERRAIN_TYPES = {
    -1: ("unexplored",  "#757575"),
     0: ("none",        "#6F4E37"),
     1: ("water",       "#2196F3"),
     2: ("under water", "#0277BD"),
     3: ("air",         "#B3E5FC"),
     4: ("desert",      "#CBBD93"),
     5: ("arctic",      "#FFFAFA"),
     6: ("mountain",    "#6D778F"),
     7: ("meadow",      "#80EF80"),
     8: ("forest",      "#228B22"),
     9: ("beach",       "#ECD540"),
    10: ("swamp",       "#7E8C54"),
    11: ("town",        "#C3BFBF"),
    12: ("jungle",      "#40826d"),
    13: ("cave",        "#353839"),
}

ROAD_COLOUR = "#A2A0A0"
PATH_COLOUR = "#6F4E37"