# ui/widgets/mapper/utils.py

import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPolygonF, QBrush, QPen
from PySide6.QtWidgets import QGraphicsPolygonItem

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
    """Creates a triangular arrowhead at the 'end' of a line pointing from 'start'."""
    dx, dy = end.x() - start.x(), end.y() - start.y()
    distance = math.hypot(dx, dy)
    if distance == 0:
        return QGraphicsPolygonItem()

    ux, uy = dx / distance, dy / distance  # unit vector
    px, py = -uy, ux                       # perpendicular unit vector

    tip   = QPointF(end.x() + ux * 0.5, end.y() + uy * 0.5)
    left  = QPointF(end.x() - ux * size + px * size, end.y() - uy * size + py * size)
    right = QPointF(end.x() - ux * size - px * size, end.y() - uy * size - py * size)

    arrow = QGraphicsPolygonItem(QPolygonF([tip, left, right]))
    arrow.setBrush(QBrush(color))
    arrow.setPen(QPen(color))
    arrow.setZValue(Z_ROOM_ICON)
    return arrow
