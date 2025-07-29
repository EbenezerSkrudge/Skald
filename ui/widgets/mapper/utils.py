# ui/widgets/mapper/utils.py

import math
from functools import lru_cache

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPolygonF, QBrush, QPen, QFont
from PySide6.QtWidgets import QGraphicsPolygonItem

from game.terrain import TERRAIN_TYPES
from ui.widgets.mapper.constants import Z_ROOM_ICON


def shorten_line(start: QPointF, end: QPointF, offset: float) -> QPointF:
    """Returns a point offset back from 'end' along the line from 'start'."""
    dx, dy = end.x() - start.x(), end.y() - start.y()
    distance = math.hypot(dx, dy)
    if distance == 0:
        return QPointF(end)

    ux, uy = dx / distance, dy / distance
    return QPointF(end.x() - ux * offset, end.y() - uy * offset)


def create_arrowhead(start: QPointF, end: QPointF, color: QColor, size: float = 4) -> QGraphicsPolygonItem:
    dx, dy = end.x() - start.x(), end.y() - start.y()
    d = math.hypot(dx, dy)
    if d == 0:
        return QGraphicsPolygonItem()

    ux, uy = dx / d, dy / d
    poly = arrowhead_points(ux, uy, size)

    # Translate the polygon to the endpoint
    translated_poly = QPolygonF([p + end for p in poly])  # type: ignore
    arrow = QGraphicsPolygonItem(translated_poly)
    arrow.setBrush(QBrush(color))
    arrow.setPen(QPen(color))
    arrow.setZValue(Z_ROOM_ICON)
    return arrow


# Cache for QColor objects by terrain name
_TERRAIN_COLOR_CACHE = {}


def get_terrain_color(terrain: str) -> QColor:
    if terrain not in _TERRAIN_COLOR_CACHE:
        hex_code = TERRAIN_TYPES.get(terrain, ("?", "#555"))[1]
        _TERRAIN_COLOR_CACHE[terrain] = QColor(hex_code)
    return _TERRAIN_COLOR_CACHE[terrain]


# Cache fonts keyed by size
_FONT_CACHE = {}


def get_bold_font(size: float) -> QFont:
    key = round(size, 1)
    if key not in _FONT_CACHE:
        font = QFont()
        font.setPointSizeF(key)
        font.setBold(True)
        _FONT_CACHE[key] = font
    return _FONT_CACHE[key]


# Cache arrowheads
@lru_cache(maxsize=128)
def arrowhead_points(ux: float, uy: float, size: float) -> QPolygonF:
    px, py = -uy, ux
    tip = QPointF(ux * 0.5, uy * 0.5)
    left = QPointF(-ux * size + px * size, -uy * size + py * size)
    right = QPointF(-ux * size - px * size, -uy * size - py * size)
    return QPolygonF([tip, left, right])


def split_suffix(dir_text: str) -> tuple[str, str | None]:
    txt = dir_text.lower()
    if txt.endswith("up"):
        return txt[:-2], "up"
    if txt.endswith("down"):
        return txt[:-4], "down"
    return txt, None


def midpoint(p1: QPointF, p2: QPointF) -> QPointF:
    return QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)