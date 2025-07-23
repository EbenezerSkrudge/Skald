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
    QPen, QBrush, QLinearGradient, QColor, QTransform, QPolygonF, Qt
)
from PySide6.QtCore import QRectF, QPointF, QLineF

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
    """
    A simple line between two RoomIcon.scenePos() points,
    accepts hover events to highlight when under the cursor.
    """

    def __init__(self, icon_a, icon_b, color=Qt.darkGray, width=5):
        super().__init__()
        self.icon_a = icon_a
        self.icon_b = icon_b

        # Normal vs hover pens
        self._normal_pen = QPen(QColor(color), width)
        self._hover_pen  = QPen(QColor(Qt.cyan), width + 1)

        self.setPen(self._normal_pen)
        self.setZValue(Z_CONNECTOR)

        # Enable hover events
        self.setAcceptHoverEvents(True)

        # Initial draw
        self.refresh()

    def refresh(self):
        p1 = self.icon_a.scenePos()
        p2 = self.icon_b.scenePos()
        self.setLine(QLineF(p1, p2))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)
        super().hoverLeaveEvent(event)

    def add_to_scene(self, scene):
        scene.addItem(self)


class BorderConnectorItem(QGraphicsPolygonItem):
    """
    A little arrow + shaft indicating a 'border' link.
    Also highlights on hover.
    """

    def __init__(self, icon_a, icon_b=None, target_pos=None,
                 arrow_size=8, shaft_length=16, color=Qt.yellow):
        super().__init__()
        self.icon_a     = icon_a
        self.icon_b     = icon_b
        self.target_pos = target_pos
        self.arrow_size = arrow_size
        self.shaft_len  = shaft_length

        # Pens for normal vs hover
        self._normal_pen = QPen(QColor(color), 4)
        self._hover_pen  = QPen(QColor(Qt.cyan), 5)

        self.setPen(self._normal_pen)
        self.setBrush(QBrush(QColor(color)))
        self.setZValue(Z_CONNECTOR)

        # Build the shaft as a child line item
        self.shaft = QGraphicsLineItem(self)
        self.shaft.setPen(self._normal_pen)
        self.shaft.setZValue(Z_CONNECTOR - 1)

        # Build the arrowhead polygon (pointing up at local origin)
        h = arrow_size
        w = arrow_size * 0.6
        self._base_poly = QPolygonF([
            QPointF(0, -h),
            QPointF(-w, 0),
            QPointF( w, 0),
        ])
        self.setPolygon(self._base_poly)

        # Enable hover events
        self.setAcceptHoverEvents(True)
        self.shaft.setAcceptHoverEvents(True)

        # Initial draw/position
        self.refresh()

    def refresh(self):
        # Anchor and target positions in scene coords
        p1 = self.icon_a.scenePos()
        p2 = self.target_pos or self.icon_b.scenePos()

        # Midpoint for placing the arrowhead
        mid = QPointF((p1.x() + p2.x()) / 2,
                      (p1.y() + p2.y()) / 2)

        # Compute rotation angle (0° = east, 90° = north)
        angle = QLineF(p1, p2).angle()

        # Rotate & move arrowhead
        self.setRotation(-angle + 90)
        self.setPos(mid)

        # Draw shaft *behind* the arrow
        # Local coords: tip at (0,0), shaft extends further back (positive Y)
        tip  = QPointF(0, 0)
        back = QPointF(0, self.shaft_len)
        self.shaft.setLine(QLineF(tip, back))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)
        self.shaft.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)
        self.shaft.setPen(self._normal_pen)
        super().hoverLeaveEvent(event)

    def add_to_scene(self, scene):
        scene.addItem(self)



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