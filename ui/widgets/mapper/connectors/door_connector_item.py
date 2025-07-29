# ui/widgets/mapper/connectors/door_connector_item.py

import math

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QTransform
from PySide6.QtWidgets import QGraphicsRectItem

from ui.widgets.mapper.connectors.connector_item import ConnectorItem
from ui.widgets.mapper.constants import Z_ROOM_SHAPE
from ui.widgets.mapper.utils import midpoint


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
