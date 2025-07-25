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
    """Displays the player location as a circle with an optional directional arrow."""

    _DIRECTIONS = {
        1: (-1,  1), 2: (0, 1), 3: (1,  1),
        4: (-1,  0),            6: (1,  0),
        7: (-1, -1), 8: (0, -1), 9: (1, -1),
    }

    def __init__(self, grid_x, grid_y, direction_code=None,
                 radius=16, arrow_length=8, arrow_width=8):
        super().__init__()

        self.radius = radius
        self.arrow_length = arrow_length
        self.arrow_width = arrow_width

        self._init_circle()
        self._init_arrow()

        self.setZValue(Z_ROOM_ICON + 1)
        self.update_position(grid_x, grid_y)
        self.update_direction(direction_code)

    def _init_circle(self):
        """Creates the red circular location marker."""
        r = self.radius
        circle = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        circle.setPen(QPen(QColor("red"), 5))
        circle.setBrush(Qt.NoBrush)
        circle.setGraphicsEffect(self._make_shadow(blur=12, offset=(4, 4)))
        self.addToGroup(circle)

    def _init_arrow(self):
        """Creates the optional directional arrow."""
        self.arrow = QGraphicsPolygonItem(QPolygonF())
        self.arrow.setBrush(QBrush(QColor("red")))
        self.arrow.setPen(QPen(QColor("red")))
        self.arrow.setGraphicsEffect(self._make_shadow(blur=8, offset=(3, 3)))
        self.arrow.setVisible(False)
        self.addToGroup(self.arrow)

    def _make_shadow(self, blur, offset):
        """Returns a black drop shadow effect."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setOffset(*offset)
        shadow.setColor(QColor(0, 0, 0, 160))
        return shadow

    def update_position(self, grid_x, grid_y):
        """Moves the widget to the specified grid cell."""
        self.setPos(QPointF(grid_x * GRID_SIZE, grid_y * GRID_SIZE))

    def update_direction(self, code):
        """Updates the arrow to point in the direction represented by `code`."""
        direction = self._DIRECTIONS.get(code)
        if not direction:
            self.arrow.setVisible(False)
            return

        dx, dy = direction
        length = math.hypot(dx, dy)
        if length == 0:
            self.arrow.setVisible(False)
            return

        # Normalize vector
        ux, uy = dx / length, dy / length

        # Points: tip, base left, base right
        tip = QPointF(ux * self.radius, uy * self.radius)

        base_dist = self.radius - self.arrow_length
        base_center = QPointF(ux * base_dist, uy * base_dist)

        # Perpendicular vector for width
        px, py = -uy, ux
        half_w = self.arrow_width / 2
        left  = QPointF(base_center.x() + px * half_w, base_center.y() + py * half_w)
        right = QPointF(base_center.x() - px * half_w, base_center.y() - py * half_w)

        # Set polygon and show
        self.arrow.setPolygon(QPolygonF([tip, left, right]))
        self.arrow.setVisible(True)
