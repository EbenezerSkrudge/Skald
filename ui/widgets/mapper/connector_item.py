# ui/widgets/mapper/connector_item.py

import math

from PySide6.QtCore import QRectF, QPointF, QLineF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QTransform, QPolygonF, Qt
)
from PySide6.QtWidgets import (
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsItemGroup, QGraphicsPolygonItem
)

from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE, Z_ROOM_ICON
from ui.widgets.mapper.utils import shorten_line, create_arrowhead


def midpoint(p1: QPointF, p2: QPointF) -> QPointF:
    return QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)


class ConnectorItem(QGraphicsLineItem):
    """A basic line between two room icons that highlights on hover."""

    def __init__(self, icon_a, icon_b, color=Qt.darkGray, width=5):
        super().__init__()
        self.icon_a, self.icon_b = icon_a, icon_b
        self._normal_pen = QPen(QColor(color), width)
        self._hover_pen = QPen(Qt.cyan, width + 1)

        self.setPen(self._normal_pen)
        self.setZValue(Z_CONNECTOR)
        self.setAcceptHoverEvents(True)
        self.refresh()

    def refresh(self):
        self.setLine(QLineF(self.icon_a.scenePos(), self.icon_b.scenePos()))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)

    def add_to_scene(self, scene):
        scene.addItem(self)


class BorderConnectorItem(QGraphicsPolygonItem):
    """An arrow indicating a border connection with hover highlight."""

    def __init__(self, icon_a, icon_b=None, target_pos=None, arrow_size=8, shaft_length=16, color=Qt.yellow):
        super().__init__()
        self.icon_a = icon_a
        self.icon_b = icon_b
        self.target_pos = target_pos
        self.arrow_size = arrow_size
        self.shaft_len = shaft_length

        self._normal_pen = QPen(QColor(color), 4)
        self._hover_pen = QPen(Qt.cyan, 5)

        self.setPen(self._normal_pen)
        self.setBrush(QBrush(QColor(color)))
        self.setZValue(Z_CONNECTOR)

        self.shaft = QGraphicsLineItem(self)
        self.shaft.setPen(self._normal_pen)
        self.shaft.setZValue(Z_CONNECTOR - 1)

        self._base_poly = QPolygonF([
            QPointF(0, -arrow_size),
            QPointF(-arrow_size * 0.6, 0),
            QPointF(+arrow_size * 0.6, 0),
        ])
        self.setPolygon(self._base_poly)

        self.setAcceptHoverEvents(True)
        self.shaft.setAcceptHoverEvents(True)
        self.refresh()

    def refresh(self):
        p1 = self.icon_a.scenePos()
        p2 = self.target_pos or self.icon_b.scenePos()
        mid = midpoint(p1, p2)
        angle = QLineF(p1, p2).angle()

        self.setRotation(-angle + 90)
        self.setPos(mid)
        self.shaft.setLine(QLineF(QPointF(0, 0), QPointF(0, self.shaft_len)))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)
        self.shaft.setPen(self._hover_pen)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)
        self.shaft.setPen(self._normal_pen)

    def add_to_scene(self, scene):
        scene.addItem(self)


class DoorConnectorItem(ConnectorItem):
    """A connector line with an open/closed door rectangle overlay."""

    def __init__(self, room_a, room_b, door_open=True):
        self.door_open = door_open
        self.symbol_item = QGraphicsRectItem()
        super().__init__(room_a, room_b)
        self.symbol_item.setParentItem(self)
        self.symbol_item.setZValue(Z_ROOM_SHAPE)
        self.refresh()

    def refresh(self):
        super().refresh()
        line = self.line()
        mid = midpoint(line.p1(), line.p2())

        self.symbol_item.setRect(QRectF(mid.x() - 15, mid.y() - 3, 30, 6))

        angle = math.degrees(math.atan2(line.dy(), line.dx()))
        rotation = angle + (45 if self.door_open else 90)

        brush_color = QColor("lime" if self.door_open else "red")
        pen_color = QColor("white" if self.door_open else "black")

        self.symbol_item.setBrush(QBrush(brush_color))
        self.symbol_item.setPen(QPen(pen_color, 1))

        transform = (
            QTransform()
            .translate(mid.x(), mid.y())
            .rotate(rotation)
            .translate(-mid.x(), -mid.y())
        )
        self.symbol_item.setTransform(transform)


class DoorBorderConnectorItem(QGraphicsItemGroup):
    """Border connector with a shortened line and door rectangle."""

    def __init__(
            self, icon_a, icon_b=None, target_pos=None, door_open=True,
            line_color=Qt.yellow, line_width=6, door_size=(30, 6), shaft_shrink=20
    ):
        super().__init__()
        self.icon_a, self.icon_b = icon_a, icon_b
        self.target_pos = target_pos
        self.door_open = door_open
        self.door_w, self.door_h = door_size
        self.shaft_shrink = shaft_shrink

        self._normal_pen = QPen(QColor(line_color), line_width)
        self._hover_pen = QPen(Qt.cyan, line_width + 1)

        self.line_item = QGraphicsLineItem(parent=self)
        self.line_item.setPen(self._normal_pen)
        self.line_item.setZValue(Z_CONNECTOR)
        self.line_item.setAcceptHoverEvents(True)
        self.line_item.hoverEnterEvent = self.hoverEnterEvent
        self.line_item.hoverLeaveEvent = self.hoverLeaveEvent

        self.rect_item = QGraphicsRectItem(parent=self)
        fill = QColor("lime" if door_open else "red")
        border = QColor("white" if door_open else "black")
        self.rect_item.setBrush(QBrush(fill))
        self.rect_item.setPen(QPen(border, 1))
        self.rect_item.setZValue(Z_ROOM_SHAPE)

        self.setAcceptHoverEvents(True)
        self.setZValue(Z_CONNECTOR)
        self.refresh()

    def refresh(self):
        p1 = self.icon_a.scenePos()
        p2 = self.target_pos or self.icon_b.scenePos()
        mid = midpoint(p1, p2)
        angle = QLineF(p1, p2).angle()
        self.setPos(mid)
        self.setRotation(-angle)

        dist = QLineF(p1, p2).length()
        half = max((dist / 2) - self.shaft_shrink, 0)
        self.line_item.setLine(QLineF(QPointF(-half, 0), QPointF(half, 0)))

        self.rect_item.setRect(QRectF(-self.door_w / 2, -self.door_h / 2, self.door_w, self.door_h))
        self.rect_item.setRotation(90 if not self.door_open else 45)

    def hoverEnterEvent(self, event):
        self.line_item.setPen(self._hover_pen)

    def hoverLeaveEvent(self, event):
        self.line_item.setPen(self._normal_pen)

    def add_to_scene(self, scene):
        scene.addItem(self)


class NonCardinalDirectionTag(QGraphicsItemGroup):
    """Displays arrows for non-cardinal directions (in, out, up, down) around an icon."""

    def __init__(self, icon, directions: list[str]):
        super().__init__()
        self.setZValue(Z_ROOM_ICON)

        br = icon.boundingRect()
        center_scene = icon.mapToScene(br.center())
        cx, cy = center_scene.x(), center_scene.y()

        orange = QColor("orange")
        # TODO: Not needed if icon renders OK: arrow_pen = QPen(orange, 3)
        dash_pen = QPen(orange, 3)

        if any(d in directions for d in ("in", "out")):
            io_group = QGraphicsItemGroup(self)
            circ = QGraphicsEllipseItem(QRectF(-6, -6, 12, 12))
            circ.setPen(QPen(orange, 2))
            io_group.addToGroup(circ)

            for d in ("in", "out"):
                if d not in directions:
                    continue
                start, end = (
                    (QPointF(7, 7), QPointF(-2, -2)) if d == "in"
                    else (QPointF(0, 0), QPointF(9, 9))
                )
                se = shorten_line(start, end, 2)
                io_group.addToGroup(QGraphicsLineItem(start.x(), start.y(), se.x(), se.y()))
                io_group.addToGroup(create_arrowhead(start, end, orange))

            io_group.setPos(cx + 30, cy + 11)
            io_group.setZValue(Z_ROOM_ICON)

        if any(d in directions for d in ("up", "down")):
            ud_group = QGraphicsItemGroup(self)
            for x in (-5, 6):
                dash = QGraphicsLineItem(x - 1, 0, x, 0)
                dash.setPen(dash_pen)
                ud_group.addToGroup(dash)

            for d in ("up", "down"):
                if d not in directions:
                    continue
                y = 6
                start, end = (
                    (QPointF(0, y), QPointF(0, -y - 2)) if d == "up"
                    else (QPointF(0, -y), QPointF(0, y + 2))
                )
                se = shorten_line(start, end, 2)
                ud_group.addToGroup(QGraphicsLineItem(start.x(), start.y(), se.x(), se.y()))
                ud_group.addToGroup(create_arrowhead(start, end, orange))

            ud_group.setPos(cx + 31, cy - 12)
            ud_group.setZValue(Z_ROOM_ICON)
