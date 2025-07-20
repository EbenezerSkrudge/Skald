from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem
)
from PySide6.QtGui import QBrush, QPen, QColor, QFont
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import (
    Z_ROOM_SHAPE,
    Z_ROOM_ICON,
    GRID_SIZE,
    ROOM_SIZE
)

class RoomItem(QGraphicsItemGroup):
    def __init__(
        self,
        grid_x: int,
        grid_y: int,
        short_desc: str,
        color: QColor,
        explored: bool = True
    ):
        super().__init__()

        # grid → pixel center
        self.grid_x     = grid_x
        self.grid_y     = grid_y
        self.pos        = QPointF(grid_x * GRID_SIZE,
                                   grid_y * GRID_SIZE)

        # keep the GMCP short‐desc around for the tooltip
        self.short_desc = short_desc

        # fixed diameter & style
        self.size       = ROOM_SIZE
        self.color      = color
        self.explored   = explored

        self._build_visuals()
        self.setZValue(Z_ROOM_SHAPE + 1)

        # use the short description as a hover tooltip
        self.setToolTip(self.short_desc)

    def _build_visuals(self):
        # clear out any old items
        for child in self.childItems():
            self.removeFromGroup(child)
            child.setParentItem(None)

        half = self.size / 2

        # ---------- room shape ----------
        if self.explored:
            shape = QGraphicsRectItem(
                self.pos.x() - half,
                self.pos.y() - half,
                self.size,
                self.size
            )
            shape.setBrush(QBrush(self.color))
        else:
            shape = QGraphicsEllipseItem(
                self.pos.x() - half,
                self.pos.y() - half,
                self.size,
                self.size
            )
            shape.setBrush(QBrush(QColor("#555")))
            shape.setPen(QPen(QColor("darkgray"), 1))

        shape.setZValue(Z_ROOM_SHAPE)
        self.addToGroup(shape)

        # ---------- “?” for unexplored ----------
        if not self.explored:
            icon = QGraphicsTextItem("?")
            icon.setDefaultTextColor(QColor("yellow"))

            f = icon.font()
            f.setPointSizeF(self.size * 0.5)
            f.setBold(True)
            icon.setFont(f)

            br = icon.boundingRect()
            icon.setPos(
                self.pos.x() - br.width()  / 2,
                self.pos.y() - br.height() / 2
            )
            icon.setZValue(Z_ROOM_ICON)
            self.addToGroup(icon)

    def center(self) -> QPointF:
        return QPointF(self.pos)

    def get_color(self) -> QColor:
        return self.color

    def set_explored(self, explored: bool):
        self.explored = explored
        self._build_visuals()
