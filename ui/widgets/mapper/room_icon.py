# ui/widgets/mapper/room_icon.py

from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
    QGraphicsItem
)
from PySide6.QtGui import QBrush, QPen, QColor, Qt
from PySide6.QtCore import QPointF

from ui.widgets.mapper.constants import (
    Z_ROOM_SHAPE, Z_ROOM_ICON, GRID_SIZE, ROOM_SIZE
)
from game.terrain import TERRAIN_TYPES


class RoomIcon(QGraphicsItemGroup):
    def __init__(self, grid_x: int, grid_y: int, short_desc: str, terrain: str):
        super().__init__()

        self.grid_x = grid_x
        self.grid_y = grid_y
        self.pos = QPointF(grid_x * GRID_SIZE, grid_y * GRID_SIZE)
        self.short_desc = short_desc
        self.terrain = terrain
        self.size = ROOM_SIZE

        self.setToolTip(short_desc)
        self.setZValue(Z_ROOM_SHAPE + 1)
        self.setAcceptedMouseButtons(Qt.RightButton)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        self._build_visuals()

    def _build_visuals(self):
        for child in self.childItems():
            self.removeFromGroup(child)
            child.setParentItem(None)

        half = self.size / 2
        x, y = self.pos.x() - half, self.pos.y() - half
        terrain_color = TERRAIN_TYPES.get(self.terrain, ("unknown", "#555"))[1]
        color = QColor(terrain_color)

        if self.terrain == "unexplored":
            shape = QGraphicsEllipseItem(x, y, self.size, self.size)
            shape.setBrush(QBrush(color))
            shape.setPen(QPen(QColor("darkgray"), 1))
            shape.setZValue(Z_ROOM_SHAPE)
            self.addToGroup(shape)

            icon = QGraphicsTextItem("?")
            font = icon.font()
            font.setPointSizeF(self.size * 0.5)
            font.setBold(True)
            icon.setFont(font)
            icon.setDefaultTextColor(QColor("gray"))

            br = icon.boundingRect()
            icon.setPos(self.pos.x() - br.width() / 2, self.pos.y() - br.height() / 2)
            icon.setZValue(Z_ROOM_ICON)
            self.addToGroup(icon)
        else:
            shape = QGraphicsRectItem(x, y, self.size, self.size)
            shape.setBrush(QBrush(color))
            shape.setZValue(Z_ROOM_SHAPE)
            self.addToGroup(shape)

        # Selection overlay if selected
        if self.isSelected():
            pad = 2
            overlay_shape = (
                QGraphicsEllipseItem if self.terrain == "unexplored"
                else QGraphicsRectItem
            )
            border = overlay_shape(x - pad, y - pad, self.size + pad * 2, self.size + pad * 2)
            border.setPen(QPen(QColor("cyan"), 2))
            border.setBrush(QBrush(QColor(0, 255, 255, 60)))
            border.setZValue(Z_ROOM_ICON + 1)
            self.addToGroup(border)

    def center(self) -> QPointF:
        return self.pos

    def itemChange(self, change, value):
        if change in (
            QGraphicsItem.ItemSelectedChange,
            QGraphicsItem.ItemSelectedHasChanged
        ):
            self._build_visuals()
        return super().itemChange(change, value)

    def refresh(self):
        self._build_visuals()