from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
)
from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtCore import QPointF

from ui.widgets.mapper.constants import (
    Z_ROOM_SHAPE,
    Z_ROOM_ICON,
    GRID_SIZE,
    ROOM_SIZE,
)


class RoomItem(QGraphicsItemGroup):
    def __init__(self, grid_x: int, grid_y: int, short_desc: str, color: QColor, explored: bool = True):
        super().__init__()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.pos = QPointF(grid_x * GRID_SIZE, grid_y * GRID_SIZE)
        self.short_desc = short_desc
        self.color = color
        self.explored = explored
        self.size = ROOM_SIZE

        self.setZValue(Z_ROOM_SHAPE + 1)
        self.setToolTip(short_desc)
        self._build_visuals()

    def _build_visuals(self):
        for child in self.childItems():
            self.removeFromGroup(child)
            child.setParentItem(None)

        half = self.size / 2
        x, y = self.pos.x() - half, self.pos.y() - half

        if self.explored:
            shape = QGraphicsRectItem(x, y, self.size, self.size)
            shape.setBrush(QBrush(self.color))
        else:
            shape = QGraphicsEllipseItem(x, y, self.size, self.size)
            shape.setBrush(QBrush(QColor("#555")))
            shape.setPen(QPen(QColor("darkgray"), 1))

            icon = QGraphicsTextItem("?")
            font = icon.font()
            font.setPointSizeF(self.size * 0.5)
            font.setBold(True)
            icon.setFont(font)
            icon.setDefaultTextColor(QColor("yellow"))

            br = icon.boundingRect()
            icon.setPos(self.pos.x() - br.width() / 2, self.pos.y() - br.height() / 2)
            icon.setZValue(Z_ROOM_ICON)
            self.addToGroup(icon)

        shape.setZValue(Z_ROOM_SHAPE)
        self.addToGroup(shape)

    def center(self) -> QPointF:
        return self.pos

    def get_color(self) -> QColor:
        return self.color

    def set_explored(self, explored: bool):
        self.explored = explored
        self._build_visuals()
