import math
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem, \
    QGraphicsItemGroup, QGraphicsPolygonItem
from PySide6.QtGui import (
    QPen, QBrush, QLinearGradient, QColor, QTransform, QPolygonF
)
from PySide6.QtCore import QRectF, Qt, QPointF

from ui.widgets.mapper.constants import (
    Z_CONNECTOR,
    Z_ROOM_SHAPE,
    Z_ROOM_ICON
)

# ─────────────────────────────────────────────────────────────
# Standard connector between two rooms
# ─────────────────────────────────────────────────────────────
class ConnectorItem(QGraphicsLineItem):
    def __init__(self, room_a, room_b):
        x1 = room_a.center().x()
        y1 = room_a.center().y()
        x2 = room_b.center().x()
        y2 = room_b.center().y()

        super().__init__(x1, y1, x2, y2)

        color_a = room_a.get_color()
        color_b = room_b.get_color()

        gradient = QLinearGradient(x1, y1, x2, y2)
        gradient.setColorAt(0.0, color_a)
        gradient.setColorAt(1.0, color_b)

        pen = QPen()
        pen.setBrush(QBrush(gradient))
        pen.setWidth(4)

        self.setPen(pen)
        self.setZValue(Z_CONNECTOR)

# ─────────────────────────────────────────────────────────────
# Connector with a door symbol (open/closed)
# ─────────────────────────────────────────────────────────────
class DoorConnectorItem(ConnectorItem):
    def __init__(self, room_a, room_b, door_open: bool = True):
        super().__init__(room_a, room_b)

        self.door_open = door_open

        # Connector endpoints
        x1 = self.line().x1()
        y1 = self.line().y1()
        x2 = self.line().x2()
        y2 = self.line().y2()

        # Midpoint
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Door symbol dimensions
        symbol_width = 6
        symbol_length = 30

        symbol_rect = QRectF(
            mid_x - symbol_length / 2,
            mid_y - symbol_width / 2,
            symbol_length,
            symbol_width
        )

        self.symbol_item = QGraphicsRectItem(symbol_rect)

        # Compute connector angle
        dx = x2 - x1
        dy = y2 - y1
        angle = math.degrees(math.atan2(dy, dx))

        # Style and rotation
        if self.door_open:
            rotation = angle + 45
            self.symbol_item.setBrush(QBrush(QColor("lime")))
            self.symbol_item.setPen(QPen(QColor("white"), 1))
        else:
            rotation = angle + 90
            self.symbol_item.setBrush(QBrush(QColor("red")))
            self.symbol_item.setPen(QPen(QColor("black"), 1))

        transform = QTransform()
        transform.translate(mid_x, mid_y)
        transform.rotate(rotation)
        transform.translate(-mid_x, -mid_y)
        self.symbol_item.setTransform(transform)

        self.symbol_item.setZValue(Z_ROOM_SHAPE)

    def add_to_scene(self, scene):
        scene.addItem(self)
        scene.addItem(self.symbol_item)

# ─────────────────────────────────────────────────────────────
# Directional exit for non-cardinal directions (in/out/up/down)
# ─────────────────────────────────────────────────────────────

class NonCardinalDirectionTag(QGraphicsItemGroup):
    def __init__(self, room, directions: list[str]):
        """
        room:    object with .center(), .size
        directions: list containing any of "in","out","up","down"
        """
        super().__init__()

        # ── Shared constants ─────────────────────────────────────
        radius           = 6   # for in/out circle
        io_arrow_length  = 7
        ud_arrow_length  = 3
        tip_offset       = 2
        dash_length      = 2
        dash_gap         = 5
        vertical_spacing = 6

        arrow_pen  = QPen(QColor("orange"), 2)
        dash_pen   = QPen(QColor("orange"), 3)
        circle_pen = QPen(QColor("orange"), 2)

        cx, cy = room.center().x(), room.center().y()

        # ── IN/OUT SUB‐GROUP (bottom‐right) ─────────────────────
        if any(d in directions for d in ("in","out")):
            io = QGraphicsItemGroup()   # local group for in/out

            # circle
            crect = QRectF(-radius, -radius, radius*2, radius*2)
            circ = QGraphicsEllipseItem(crect)
            circ.setPen(circle_pen)
            io.addToGroup(circ)

            # arrows
            for d in ("in","out"):
                if d not in directions:
                    continue

                if d == "in":
                    start = QPointF(io_arrow_length, io_arrow_length)
                    end   = QPointF(-2, -2)
                else:  # out
                    start = QPointF(0, 0)
                    end   = QPointF(io_arrow_length + 2, io_arrow_length + 2)

                # shaft
                se = self._shorten_line(start, end, tip_offset)
                shaft = QGraphicsLineItem(start.x(), start.y(), se.x(), se.y())
                shaft.setPen(arrow_pen)
                io.addToGroup(shaft)

                # head
                head = self._create_arrowhead(start, end)
                io.addToGroup(head)

            # position bottom‐right of room
            io.setPos(cx + 28, cy + 28)
            io.setZValue(Z_ROOM_ICON)
            self.addToGroup(io)

        # ── UP/DOWN SUB‐GROUP (top‐right) ───────────────────────
        if any(d in directions for d in ("up","down")):
            ud = QGraphicsItemGroup()   # local group for up/down

            # shared horizontal dashes at y=0
            left_dash  = QGraphicsLineItem(-dash_gap - dash_length, 0,
                                           -dash_gap, 0)
            right_dash = QGraphicsLineItem(dash_gap, 0,
                                           dash_gap + dash_length, 0)
            for dash in (left_dash, right_dash):
                dash.setPen(dash_pen)
                ud.addToGroup(dash)

            # vertical arrows
            for d in ("up","down"):
                if d not in directions:
                    continue

                if d == "up":
                    start = QPointF(0,  vertical_spacing)
                    end   = QPointF(0, -vertical_spacing - ud_arrow_length)
                else:  # down
                    start = QPointF(0, -vertical_spacing)
                    end   = QPointF(0,  vertical_spacing + ud_arrow_length)

                se    = self._shorten_line(start, end, tip_offset)
                shaft = QGraphicsLineItem(start.x(), start.y(),
                                          se.x(), se.y())
                shaft.setPen(arrow_pen)
                ud.addToGroup(shaft)

                head = self._create_arrowhead(start, end)
                ud.addToGroup(head)

            # position top‐right of room
            ud.setPos(cx + 29, cy - 28)
            ud.setZValue(Z_ROOM_ICON)
            self.addToGroup(ud)

        # ensure overall tag is on top
        self.setZValue(Z_ROOM_ICON)

    def _shorten_line(self, start: QPointF, end: QPointF, offset: float) -> QPointF:
        dx, dy = end.x() - start.x(), end.y() - start.y()
        dist   = math.hypot(dx, dy)
        if dist == 0:
            return end
        ux, uy = dx / dist, dy / dist
        return QPointF(end.x() - ux * offset, end.y() - uy * offset)

    def _create_arrowhead(self,
                          start: QPointF,
                          end: QPointF,
                          size: float = 4
                         ) -> QGraphicsPolygonItem:
        dx, dy = end.x() - start.x(), end.y() - start.y()
        dist   = math.hypot(dx, dy)
        if dist == 0:
            return QGraphicsPolygonItem()

        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux

        tip   = QPointF(end.x() + ux * 0.5, end.y() + uy * 0.5)
        left  = QPointF(end.x() - ux * size + px * size,
                        end.y() - uy * size + py * size)
        right = QPointF(end.x() - ux * size - px * size,
                        end.y() - uy * size - py * size)

        poly = QPolygonF([tip, left, right])
        head = QGraphicsPolygonItem(poly)
        head.setBrush(QBrush(QColor("orange")))
        head.setPen(QPen(QColor("orange")))
        head.setZValue(Z_ROOM_ICON)
        return head
