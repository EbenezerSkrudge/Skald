# ui/widgets/mapper/connectors/door_border_connector_item.py

from PySide6.QtCore import QLineF, QPointF, QRectF
from PySide6.QtGui import Qt, QPen, QColor, QBrush
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsLineItem, QGraphicsRectItem

from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE
from ui.widgets.mapper.utils import midpoint


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
