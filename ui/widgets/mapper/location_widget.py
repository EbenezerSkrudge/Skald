# ui/widgets/mapper/location_widget.py

import math
from PySide6.QtWidgets import (
    QGraphicsItemGroup, QGraphicsEllipseItem,
    QGraphicsPolygonItem, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPen, QBrush, QColor, QPolygonF
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import GRID_SIZE, Z_ROOM_ICON


class LocationWidget(QGraphicsItemGroup):
    _DIR_VECTORS = {
        1: (-1, 1),  2: (0, 1),  3: (1, 1),
        4: (-1, 0),              6: (1, 0),
        7: (-1, -1), 8: (0, -1), 9: (1, -1)
    }

    def __init__(self, grid_x, grid_y, direction_code=None,
                 radius=16, arrow_length=8, arrow_width=8):
        super().__init__()
        self.radius = radius
        self.arrow_length = arrow_length
        self.arrow_width = arrow_width

        self._build_circle()
        self._build_arrow()

        self.setZValue(Z_ROOM_ICON + 1)
        self.update_position(grid_x, grid_y)
        self.update_direction(direction_code)

    def _build_circle(self):
        circ = QGraphicsEllipseItem(
            -self.radius, -self.radius,
            self.radius * 2, self.radius * 2
        )
        circ.setPen(QPen(QColor("red"), 5))
        circ.setBrush(QBrush(Qt.NoBrush))
        circ.setGraphicsEffect(self._make_shadow(blur=12, offset=(4, 4)))
        self.addToGroup(circ)

    def _build_arrow(self):
        arrow = QGraphicsPolygonItem(QPolygonF([QPointF()] * 3))
        arrow.setBrush(QBrush(QColor("red")))
        arrow.setPen(QPen(QColor("red")))
        arrow.setGraphicsEffect(self._make_shadow(blur=8, offset=(3, 3)))
        arrow.setVisible(False)
        self.arrow = arrow
        self.addToGroup(arrow)

    def _make_shadow(self, blur, offset):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(*offset)
        shadow.setColor(QColor(0, 0, 0, 160))
        return shadow

    def update_position(self, grid_x, grid_y):
        self.setPos(QPointF(grid_x * GRID_SIZE, grid_y * GRID_SIZE))

    def update_direction(self, code):
        vec = self._DIR_VECTORS.get(code)
        if not vec:
            self.arrow.setVisible(False)
            return

        dx, dy = vec
        dist = math.hypot(dx, dy)
        if dist == 0:
            self.arrow.setVisible(False)
            return

        ux, uy = dx / dist, dy / dist
        tip = QPointF(ux * self.radius, uy * self.radius)
        base_center = QPointF(
            ux * (self.radius - self.arrow_length),
            uy * (self.radius - self.arrow_length)
        )

        px, py = -uy, ux
        half_w = self.arrow_width / 2
        left  = QPointF(base_center.x() + px * half_w, base_center.y() + py * half_w)
        right = QPointF(base_center.x() - px * half_w, base_center.y() - py * half_w)

        self.arrow.setPolygon(QPolygonF([tip, left, right]))
        self.arrow.setVisible(True)
