import re
import html

# --- ANSI Constants
ESC = '\x1b'
ANSI_SGR_SPLIT_RE = re.compile(f'({re.escape(ESC)}\\[[0-9;]*m)')
SGR_TO_CSS = {
    0: 'reset', 1: 'font-weight:bold',
    30: 'color:black', 31: 'color:red',
    32: 'color:green', 33: 'color:yellow',
    34: 'color:blue', 35: 'color:magenta',
    36: 'color:cyan', 37: 'color:white',
    90: 'color:darkgray', 91: 'color:lightcoral',
    92: 'color:lightgreen', 93: 'color:lightyellow',
    94: 'color:lightblue', 95: 'color:plum',
    96: 'color:lightcyan', 97: 'color:lightgray',
}

def ansi_to_html(text: str) -> str:
    """
    Convert ANSI‐SGR sequences to inline‐CSS <span>s,
    preserving all whitespace (use in QTextEdit.insertHtml).
    """

    parts = ANSI_SGR_SPLIT_RE.split(text)
    html_chunks = []
    active_styles = []

    for part in parts:
        if not part:
            continue

        # 1) If this part _is_ an ANSI sequence
        if part.startswith(ESC) and part.endswith('m'):
            # strip ESC[  and trailing m
            codes = [int(c) for c in part[2:-1].split(';') if c.isdigit()] or [0]

            # if reset, clear styles
            if 0 in codes:
                active_styles.clear()
                continue

            # otherwise rebuild the style list
            for code in codes:
                style = SGR_TO_CSS.get(code)
                if style:
                    active_styles.append(style)
            continue

        # 2) Plain‐text chunk: escape HTML, then wrap in a span if needed
        esc = html.escape(part)
        if active_styles:
            style_str = ';'.join(active_styles)
            html_chunks.append(f'<span style="{style_str}">{esc}</span>')
        else:
            html_chunks.append(esc)

    # 3) Join & wrap in a DIV that preserves whitespace
    body = ''.join(html_chunks).replace('\n', '<br>')
    return (
        '<div style="white-space:pre-wrap; font-family:monospace; margin:0">'
        + body +
        '</div>'
    )

SIMPLE_TAGS = {
    "b":      ("<strong>",                            "</strong>"),
    "i":      ("<em>",                                "</em>"),
    "u":      ('<span style="text-decoration:underline">', "</span>"),
    "blink":  ('<span style="text-decoration:blink">',     "</span>"),
    "strike": ('<span style="text-decoration:line-through">','</span>'),
    "reverse":('<span style="filter:invert(1)">',          "</span>"),
}

PARAM_TAGS = {
    "color":   "color",
    "bgcolor": "background-color",
}

_PARAM_RE   = re.compile(r'<(color|bgcolor)=#?([0-9A-Fa-f]{6})>')
_COLOR_RE = re.compile(r'<color=([#A-Za-z0-9]+)>')
_RESET_RE   = re.compile(r'<reset>')

NAMED_COLORS = {
    "aliceblue"             : "#f0f8ff",
    "antiquewhite"          : "#faebd7",
    "aqua"                  : "#00ffff",
    "aquamarine"            : "#7fffd4",
    "azure"                 : "#f0ffff",
    "beige"                 : "#f5f5dc",
    "bisque"                : "#ffe4c4",
    "black"                 : "#000000",
    "blanchedalmond"        : "#ffebcd",
    "blue"                  : "#0000ff",
    "blueviolet"            : "#8a2be2",
    "brown"                 : "#a52a2a",
    "burlywood"             : "#deb887",
    "cadetblue"             : "#5f9ea0",
    "chartreuse"            : "#7fff00",
    "chocolate"             : "#d2691e",
    "coral"                 : "#ff7f50",
    "cornflowerblue"        : "#6495ed",
    "cornsilk"              : "#fff8dc",
    "crimson"               : "#dc143c",
    "cyan"                  : "#00ffff",
    "darkblue"              : "#00008b",
    "darkcyan"              : "#008b8b",
    "darkgoldenrod"         : "#b8860b",
    "darkgray"              : "#a9a9a9",
    "darkgreen"             : "#006400",
    "darkgrey"              : "#a9a9a9",
    "darkkhaki"             : "#bdb76b",
    "darkmagenta"           : "#8b008b",
    "darkolivegreen"        : "#556b2f",
    "darkorange"            : "#ff8c00",
    "darkorchid"            : "#9932cc",
    "darkred"               : "#8b0000",
    "darksalmon"            : "#e9967a",
    "darkseagreen"          : "#8fbc8f",
    "darkslateblue"         : "#483d8b",
    "darkslategray"         : "#2f4f4f",
    "darkslategrey"         : "#2f4f4f",
    "darkturquoise"         : "#00ced1",
    "darkviolet"            : "#9400d3",
    "deeppink"              : "#ff1493",
    "deepskyblue"           : "#00bfff",
    "dimgray"               : "#696969",
    "dimgrey"               : "#696969",
    "dodgerblue"            : "#1e90ff",
    "firebrick"             : "#b22222",
    "floralwhite"           : "#fffaf0",
    "forestgreen"           : "#228b22",
    "fuchsia"               : "#ff00ff",
    "gainsboro"             : "#dcdcdc",
    "ghostwhite"            : "#f8f8ff",
    "gold"                  : "#ffd700",
    "goldenrod"             : "#daa520",
    "gray"                  : "#808080",
    "green"                 : "#008000",
    "greenyellow"           : "#adff2f",
    "grey"                  : "#808080",
    "honeydew"              : "#f0fff0",
    "hotpink"               : "#ff69b4",
    "indianred"             : "#cd5c5c",
    "indigo"                : "#4b0082",
    "ivory"                 : "#fffff0",
    "khaki"                 : "#f0e68c",
    "lavender"              : "#e6e6fa",
    "lavenderblush"         : "#fff0f5",
    "lawngreen"             : "#7cfc00",
    "lemonchiffon"          : "#fffacd",
    "lightblue"             : "#add8e6",
    "lightcoral"            : "#f08080",
    "lightcyan"             : "#e0ffff",
    "lightgoldenrodyellow"  : "#fafad2",
    "lightgray"             : "#d3d3d3",
    "lightgreen"            : "#90ee90",
    "lightgrey"             : "#d3d3d3",
    "lightpink"             : "#ffb6c1",
    "lightsalmon"           : "#ffa07a",
    "lightseagreen"         : "#20b2aa",
    "lightskyblue"          : "#87cefa",
    "lightslategray"        : "#778899",
    "lightslategrey"        : "#778899",
    "lightsteelblue"        : "#b0c4de",
    "lightyellow"           : "#ffffe0",
    "lime"                  : "#00ff00",
    "limegreen"             : "#32cd32",
    "linen"                 : "#faf0e6",
    "magenta"               : "#ff00ff",
    "maroon"                : "#800000",
    "mediumaquamarine"      : "#66cdaa",
    "mediumblue"            : "#0000cd",
    "mediumorchid"          : "#ba55d3",
    "mediumpurple"          : "#9370db",
    "mediumseagreen"        : "#3cb371",
    "mediumslateblue"       : "#7b68ee",
    "mediumspringgreen"     : "#00fa9a",
    "mediumturquoise"       : "#48d1cc",
    "mediumvioletred"       : "#c71585",
    "midnightblue"          : "#191970",
    "mintcream"             : "#f5fffa",
    "mistyrose"             : "#ffe4e1",
    "moccasin"              : "#ffe4b5",
    "navajowhite"           : "#ffdead",
    "navy"                  : "#000080",
    "oldlace"               : "#fdf5e6",
    "olive"                 : "#808000",
    "olivedrab"             : "#6b8e23",
    "orange"                : "#ffa500",
    "orangered"             : "#ff4500",
    "orchid"                : "#da70d6",
    "palegoldenrod"         : "#eee8aa",
    "palegreen"             : "#98fb98",
    "paleturquoise"         : "#afeeee",
    "palevioletred"         : "#db7093",
    "papayawhip"            : "#ffefd5",
    "peachpuff"             : "#ffdab9",
    "peru"                  : "#cd853f",
    "pink"                  : "#ffc0cb",
    "plum"                  : "#dda0dd",
    "powderblue"            : "#b0e0e6",
    "purple"                : "#800080",
    "rebeccapurple"         : "#663399",
    "red"                   : "#ff0000",
    "rosybrown"             : "#bc8f8f",
    "royalblue"             : "#4169e1",
    "saddlebrown"           : "#8b4513",
    "salmon"                : "#fa8072",
    "sandybrown"            : "#f4a460",
    "seagreen"              : "#2e8b57",
    "seashell"              : "#fff5ee",
    "sienna"                : "#a0522d",
    "silver"                : "#c0c0c0",
    "skyblue"               : "#87ceeb",
    "slateblue"             : "#6a5acd",
    "slategray"             : "#708090",
    "slategrey"             : "#708090",
    "snow"                  : "#fffafa",
    "springgreen"           : "#00ff7f",
    "steelblue"             : "#4682b4",
    "tan"                   : "#d2b48c",
    "teal"                  : "#008080",
    "thistle"               : "#d8bfd8",
    "tomato"                : "#ff6347",
    "turquoise"             : "#40e0d0",
    "violet"                : "#ee82ee",
    "wheat"                 : "#f5deb3",
    "white"                 : "#ffffff",
    "whitesmoke"            : "#f5f5f5",
    "yellow"                : "#ffff00",
    "yellowgreen"           : "#9acd32",
}


def expand_html(text: str) -> str:
    # 1) Replace <color=nameOrHex> with <span style="color: #RRGGBB">
    def _color_repl(m: re.Match) -> str:
        key = m.group(1)
        # normalize to hex
        if key.startswith("#") and len(key) == 7:
            hexcol = key
        else:
            hexcol = NAMED_COLORS.get(key.lower(), key)
            # if name not found, we let the browser try (e.g. “teal”)
        return f'<span style="color: {hexcol}">'

    text = _COLOR_RE.sub(_color_repl, text)

    # 2) simple tags (bold, italics, etc.) as before
    for tag, (open_html, close_html) in SIMPLE_TAGS.items():
        text = text.replace(f"<{tag}>", open_html)
        text = text.replace(f"</{tag}>", close_html)

    # 3) close color spans
    text = text.replace("</color>", "</span>")

    # 4) <reset> as a generic span-close
    text = _RESET_RE.sub("</span>", text)

    return text
