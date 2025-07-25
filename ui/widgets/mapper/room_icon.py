# ui/widgets/mapper/room_icon.py

from PySide6.QtWidgets import (
    QGraphicsItemGroup, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsItem
)
from PySide6.QtGui import QBrush, QPen, QColor, Qt
from PySide6.QtCore import QPointF

from ui.widgets.mapper.constants import Z_ROOM_SHAPE, Z_ROOM_ICON, GRID_SIZE, ROOM_SIZE
from game.terrain import TERRAIN_TYPES


class RoomIcon(QGraphicsItemGroup):
    def __init__(self, grid_x: int, grid_y: int, short_desc: str, terrain: str):
        super().__init__()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.size = ROOM_SIZE
        self.terrain = terrain

        self.setToolTip(short_desc)
        self.setZValue(Z_ROOM_SHAPE + 1)
        self.setAcceptedMouseButtons(Qt.RightButton)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        self._create_background()
        if terrain == "unexplored":
            self._create_question_mark()
        self._create_selection_overlay()

        self.setPos(grid_x * GRID_SIZE, grid_y * GRID_SIZE)

    def _create_background(self):
        half = self.size / 2
        color = QColor(TERRAIN_TYPES.get(self.terrain, ("?", "#555"))[1])

        if self.terrain == "unexplored":
            item = QGraphicsEllipseItem(-half, -half, self.size, self.size)
            item.setPen(QPen(Qt.darkGray, 1))
        else:
            item = QGraphicsRectItem(-half, -half, self.size, self.size)

        item.setBrush(QBrush(color))
        item.setZValue(Z_ROOM_SHAPE)
        self._bg_item = item
        self.addToGroup(item)

    def _create_question_mark(self):
        txt = QGraphicsTextItem("?")
        font = txt.font()
        font.setPointSizeF(self.size * 0.5)
        font.setBold(True)
        txt.setFont(font)
        txt.setDefaultTextColor(Qt.gray)

        br = txt.boundingRect()
        txt.setPos(-br.width() / 2, -br.height() / 2)
        txt.setZValue(Z_ROOM_ICON)
        self.addToGroup(txt)

    def _create_selection_overlay(self):
        half = self.size / 2
        pad = 2
        shape_cls = QGraphicsEllipseItem if self.terrain == "unexplored" else QGraphicsRectItem

        overlay = shape_cls(
            -half - pad, -half - pad,
            self.size + pad * 2, self.size + pad * 2
        )
        overlay.setPen(QPen(Qt.cyan, 2))
        overlay.setBrush(QBrush(QColor(0, 255, 255, 60)))
        overlay.setZValue(Z_ROOM_ICON + 1)
        overlay.setVisible(False)

        self.overlay = overlay
        self.addToGroup(overlay)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.overlay.setVisible(bool(value))
        return super().itemChange(change, value)
