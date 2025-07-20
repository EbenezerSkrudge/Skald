# ui/widgets/mapper/connector_item.py

import math
from PySide6.QtWidgets import (
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsItemGroup, QGraphicsPolygonItem
)
from PySide6.QtGui import (
    QPen, QBrush, QLinearGradient, QColor, QTransform, QPolygonF
)
from PySide6.QtCore import QRectF, QPointF
from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE, Z_ROOM_ICON


def shorten_line(start: QPointF, end: QPointF, offset: float) -> QPointF:
    dx, dy = end.x() - start.x(), end.y() - start.y()
    dist = math.hypot(dx, dy)
    if dist == 0:
        return end
    ux, uy = dx / dist, dy / dist
    return QPointF(end.x() - ux * offset, end.y() - uy * offset)


def create_arrowhead(start: QPointF, end: QPointF, color: QColor, size: float = 4) -> QGraphicsPolygonItem:
    dx, dy = end.x() - start.x(), end.y() - start.y()
    dist = math.hypot(dx, dy)
    if dist == 0:
        return QGraphicsPolygonItem()
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux
    tip = QPointF(end.x() + ux * 0.5, end.y() + uy * 0.5)
    left = QPointF(end.x() - ux * size + px * size, end.y() - uy * size + py * size)
    right = QPointF(end.x() - ux * size - px * size, end.y() - uy * size - py * size)
    poly = QPolygonF([tip, left, right])
    arrow = QGraphicsPolygonItem(poly)
    arrow.setBrush(QBrush(color))
    arrow.setPen(QPen(color))
    arrow.setZValue(Z_ROOM_ICON)
    return arrow


class ConnectorItem(QGraphicsLineItem):
    def __init__(self, room_a, room_b):
        p1, p2 = room_a.center(), room_b.center()
        super().__init__(p1.x(), p1.y(), p2.x(), p2.y())

        gradient = QLinearGradient(p1, p2)
        gradient.setColorAt(0.0, room_a.get_color())
        gradient.setColorAt(1.0, room_b.get_color())

        pen = QPen(QBrush(gradient), 4)
        self.setPen(pen)
        self.setZValue(Z_CONNECTOR)


class DoorConnectorItem(ConnectorItem):
    def __init__(self, room_a, room_b, door_open: bool = True):
        super().__init__(room_a, room_b)
        self.door_open = door_open

        line = self.line()
        mid = QPointF((line.x1() + line.x2()) / 2, (line.y1() + line.y2()) / 2)

        rect = QRectF(mid.x() - 15, mid.y() - 3, 30, 6)
        self.symbol_item = QGraphicsRectItem(rect)

        angle = math.degrees(math.atan2(line.y2() - line.y1(), line.x2() - line.x1()))
        rotation = angle + (45 if door_open else 90)

        color = QColor("lime") if door_open else QColor("red")
        pen_color = QColor("white") if door_open else QColor("black")

        self.symbol_item.setBrush(QBrush(color))
        self.symbol_item.setPen(QPen(pen_color, 1))

        transform = QTransform().translate(mid.x(), mid.y()).rotate(rotation).translate(-mid.x(), -mid.y())
        self.symbol_item.setTransform(transform)
        self.symbol_item.setZValue(Z_ROOM_SHAPE)

    def add_to_scene(self, scene):
        scene.addItem(self)
        scene.addItem(self.symbol_item)


class NonCardinalDirectionTag(QGraphicsItemGroup):
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
    def __init__(self, origin: QPointF, direction: QPointF, color: QColor,
                 full_length: float, tip_offset: float = 2,
                 pen_width: float = 2, arrowhead_size: float = 4):
        super().__init__()

        dx, dy = direction.x(), direction.y()
        dist = math.hypot(dx, dy)
        if dist == 0:
            return

        ux, uy = dx / dist, dy / dist
        mid = QPointF(origin.x() + ux * full_length / 2,
                      origin.y() + uy * full_length / 2)

        se = shorten_line(origin, mid, tip_offset)
        shaft = QGraphicsLineItem(origin.x(), origin.y(), se.x(), se.y())
        shaft.setPen(QPen(color, pen_width))
        self.addToGroup(shaft)

        head = create_arrowhead(origin, mid, color, arrowhead_size)
        self.addToGroup(head)

        self.setZValue(Z_ROOM_SHAPE - 1)
