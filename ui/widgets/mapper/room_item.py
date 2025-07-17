from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem
)
from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtCore import QPointF

from ui.widgets.mapper.constants import (
    Z_ROOM_SHAPE,
    Z_ROOM_LABEL,
    Z_ROOM_ICON
)

class RoomItem(QGraphicsItemGroup):
    def __init__(self, pos: QPointF, size: int, label: str, color: QColor, explored: bool = True):
        super().__init__()

        self.pos = pos              # Logical center
        self.size = size
        self.label_text = label
        self.color = color
        self.explored = explored

        self._build_visuals()
        self.setZValue(Z_ROOM_SHAPE + 1)  # Ensure group is above connectors

    def _build_visuals(self):
        # Remove existing visuals
        for item in self.childItems():
            self.removeFromGroup(item)
            item.setParentItem(None)

        # Shape: square if explored, circle if unexplored
        if self.explored:
            shape_item = QGraphicsRectItem(
                self.pos.x() - self.size / 2,
                self.pos.y() - self.size / 2,
                self.size,
                self.size
            )
            shape_item.setBrush(QBrush(self.color))
            shape_item.setPen(QPen(QColor("white"), 2))
        else:
            shape_item = QGraphicsEllipseItem(
                self.pos.x() - self.size / 2,
                self.pos.y() - self.size / 2,
                self.size,
                self.size
            )
            shape_item.setBrush(QBrush(QColor("#555")))
            shape_item.setPen(QPen(QColor("darkgray"), 1))

        shape_item.setZValue(Z_ROOM_SHAPE)
        self.addToGroup(shape_item)

        # Label
        label_item = QGraphicsTextItem(self.label_text)
        label_item.setDefaultTextColor(QColor("white"))
        label_item.setPos(self.pos.x() - 20, self.pos.y() + self.size / 2 + 5)
        label_item.setZValue(Z_ROOM_LABEL)
        self.addToGroup(label_item)

        # Optional "?" icon
        if not self.explored:
            icon_item = QGraphicsTextItem("?")
            icon_item.setDefaultTextColor(QColor("yellow"))
            icon_item.setPos(self.pos.x() - 5, self.pos.y() - 10)
            icon_item.setZValue(Z_ROOM_ICON)
            self.addToGroup(icon_item)

    def center(self) -> QPointF:
        """Returns the logical center of the room."""
        return QPointF(self.pos.x(), self.pos.y())

    def get_color(self) -> QColor:
        """Returns the room's logical color."""
        return self.color

    def set_explored(self, explored: bool):
        """Updates the room's explored state and rebuilds visuals."""
        self.explored = explored
        self._build_visuals()
