# ui/widgets/mapper/connector_item.py

import math
from PySide6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsPolygonItem
)
from PySide6.QtGui import (
    QPen, QBrush, QLinearGradient, QColor, QTransform, QPolygonF
)
from PySide6.QtCore import QRectF, QPointF

from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE, Z_ROOM_ICON
from game.terrain import TERRAIN_TYPES


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


class ConnectorItem(QGraphicsLineItem):
    def __init__(self, room_a, room_b):
        # store original refs (Room or RoomIcon)
        self._raw_a = room_a
        self._raw_b = room_b
        super().__init__()
        self.setZValue(Z_CONNECTOR)
        self.refresh()

    def refresh(self):
        # resolve the actual icon and terrain for each endpoint
        if hasattr(self._raw_a, "icon"):
            icon_a = self._raw_a.icon
            terrain_a = self._raw_a.terrain
        else:
            icon_a = self._raw_a
            terrain_a = self._raw_a.terrain

        if hasattr(self._raw_b, "icon"):
            icon_b = self._raw_b.icon
            terrain_b = self._raw_b.terrain
        else:
            icon_b = self._raw_b
            terrain_b = self._raw_b.terrain

        # compute endpoints from scene positions
        p1 = icon_a.sceneBoundingRect().center()
        p2 = icon_b.sceneBoundingRect().center()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())

        # rebuild gradient pen
        hex_a = TERRAIN_TYPES.get(terrain_a, ("unknown", "#888"))[1]
        hex_b = TERRAIN_TYPES.get(terrain_b, ("unknown", "#888"))[1]
        col_a = QColor(hex_a)
        col_b = QColor(hex_b)

        grad = QLinearGradient(p1, p2)
        grad.setColorAt(0.0, col_a)
        grad.setColorAt(1.0, col_b)

        pen = QPen(QBrush(grad), 4)
        self.setPen(pen)


class DoorConnectorItem(ConnectorItem):
    """
    A ConnectorItem with a door‐symbol overlay (green=open, red=closed).
    """
    def __init__(self, room_a, room_b, door_open: bool = True):
        self.door_open = door_open
        super().__init__(room_a, room_b)

        # create the symbol once
        self.symbol_item = QGraphicsRectItem()
        self.symbol_item.setZValue(Z_ROOM_SHAPE)
        self.refresh()

    def refresh(self):
        # reposition the line
        super().refresh()

        # compute midpoint & rotation
        line = self.line()
        mid = QPointF((line.x1() + line.x2()) / 2, (line.y1() + line.y2()) / 2)

        # update symbol geometry
        rect = QRectF(mid.x() - 15, mid.y() - 3, 30, 6)
        self.symbol_item.setRect(rect)

        angle = math.degrees(math.atan2(line.y2() - line.y1(),
                                        line.x2() - line.x1()))
        rotation = angle + (45 if self.door_open else 90)

        color = QColor("lime") if self.door_open else QColor("red")
        pen_color = QColor("white") if self.door_open else QColor("black")

        self.symbol_item.setBrush(QBrush(color))
        self.symbol_item.setPen(QPen(pen_color, 1))

        xf = (QTransform()
              .translate(mid.x(), mid.y())
              .rotate(rotation)
              .translate(-mid.x(), -mid.y()))
        self.symbol_item.setTransform(xf)


class NonCardinalDirectionTag(QGraphicsItemGroup):
    """Renders in/out or up/down arrows around a room."""
    def __init__(self, room, directions: list[str]):
        super().__init__()
        cx, cy = room.center().x(), room.center().y()
        orange = QColor("orange")
        arrow_pen = QPen(orange, 2)
        dash_pen = QPen(orange, 3)

        if any(d in directions for d in ("in", "out")):
            io = QGraphicsItemGroup()
            circ = QGraphicsEllipseItem(QRectF(-6, -6, 12, 12))
            circ.setPen(QPen(orange, 2))
            io.addToGroup(circ)

            for d in ("in", "out"):
                if d not in directions:
                    continue
                start = QPointF(7, 7) if d == "in" else QPointF(0, 0)
                end = QPointF(-2, -2) if d == "in" else QPointF(9, 9)
                se = shorten_line(start, end, 2)
                shaft = QGraphicsLineItem(start.x(), start.y(), se.x(), se.y())
                shaft.setPen(arrow_pen)
                io.addToGroup(shaft)
                io.addToGroup(create_arrowhead(start, end, orange))
            io.setPos(cx + 30, cy + 11)
            io.setZValue(Z_ROOM_ICON)
            self.addToGroup(io)

        if any(d in directions for d in ("up", "down")):
            ud = QGraphicsItemGroup()
            for x in (-6, 6):
                dash = QGraphicsLineItem(x - 1, 0, x, 0)
                dash.setPen(dash_pen)
                ud.addToGroup(dash)

            for d in ("up", "down"):
                if d not in directions:
                    continue
                y = 6
                start = QPointF(0, y) if d == "up" else QPointF(0, -y)
                end = QPointF(0, -y - 2) if d == "up" else QPointF(0, y + 2)
                se = shorten_line(start, end, 2)
                shaft = QGraphicsLineItem(start.x(), start.y(), se.x(), se.y())
                shaft.setPen(arrow_pen)
                ud.addToGroup(shaft)
                ud.addToGroup(create_arrowhead(start, end, orange))
            ud.setPos(cx + 31, cy - 12)
            ud.setZValue(Z_ROOM_ICON)
            self.addToGroup(ud)

        self.setZValue(Z_ROOM_ICON)


class FoldedConnectorItem(QGraphicsItemGroup):
    """A short folded arrow indicating a continuation off-map."""
    def __init__(
        self,
        origin: QPointF,
        direction: QPointF,
        color: QColor,
        full_length: float,
        tip_offset: float = 2,
        pen_width: float = 2,
        arrowhead_size: float = 4
    ):
        super().__init__()
        dx, dy = direction.x(), direction.y()
        dist = math.hypot(dx, dy)
        if dist == 0:
            return

        ux, uy = dx / dist, dy / dist
        mid = QPointF(
            origin.x() + ux * full_length / 2,
            origin.y() + uy * full_length / 2
        )

        se = shorten_line(origin, mid, tip_offset)
        shaft = QGraphicsLineItem(origin.x(), origin.y(), se.x(), se.y())
        shaft.setPen(QPen(color, pen_width))
        self.addToGroup(shaft)

        head = create_arrowhead(origin, mid, color, arrowhead_size)
        self.addToGroup(head)

        self.setZValue(Z_ROOM_SHAPE - 1)