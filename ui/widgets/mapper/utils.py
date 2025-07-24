# ui/widgets/mapper/utils.py
import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPolygonF, QBrush, QPen
from PySide6.QtWidgets import QGraphicsPolygonItem

from ui.widgets.mapper.constants import Z_ROOM_ICON


def shorten_line(start: QPointF, end: QPointF, offset: float) -> QPointF:
    dx, dy = end.x() - start.x(), end.y() - start.y()
    d = math.hypot(dx, dy)
    if d == 0:
        return end
    ux, uy = dx / d, dy / d
    return QPointF(end.x() - ux * offset, end.y() - uy * offset)


def create_arrowhead(start: QPointF, end: QPointF, color: QColor, size: float = 4) -> QGraphicsPolygonItem:
    dx, dy = end.x() - start.x(), end.y() - start.y()
    d = math.hypot(dx, dy)
    if d == 0:
        return QGraphicsPolygonItem()
    ux, uy = dx / d, dy / d
    px, py = -uy, ux

    tip   = QPointF(end.x() + ux * 0.5, end.y() + uy * 0.5)
    left  = QPointF(end.x() - ux * size + px * size,
                    end.y() - uy * size + py * size)
    right = QPointF(end.x() - ux * size - px * size,
                    end.y() - uy * size - py * size)

    poly = QPolygonF([tip, left, right])
    arrow = QGraphicsPolygonItem(poly)
    arrow.setBrush(QBrush(color))
    arrow.setPen(QPen(color))
    arrow.setZValue(Z_ROOM_ICON)
    return arrow