# ui/widgets/mapper/location_widget.py

import math
from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsEllipseItem,
    QGraphicsPolygonItem,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPen, QBrush, QColor, QPolygonF
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import GRID_SIZE, Z_ROOM_ICON

class LocationWidget(QGraphicsItemGroup):
    # mapping numpad → (dx, dy)
    _DIR_VECTORS = {
        1: (-1,  1),
        2: ( 0,  1),
        3: ( 1,  1),
        4: (-1,  0),
        6: ( 1,  0),
        7: (-1, -1),
        8: ( 0, -1),
        9: ( 1, -1),
    }

    def __init__(
        self,
        grid_x: int,
        grid_y: int,
        direction_code: int | None,
        radius: float = 16,
        arrow_length: float = 8,
        arrow_width: float = 8
    ):
        super().__init__()

        self.radius       = radius
        self.arrow_length = arrow_length
        self.arrow_width  = arrow_width

        # draw circle + arrow container
        self._build_circle()
        self._build_arrow()

        # layer above room icons
        self.setZValue(Z_ROOM_ICON + 1)

        # position & orientation
        self.update_position(grid_x, grid_y)
        self.update_direction(direction_code)

    def _build_circle(self):
        circ = QGraphicsEllipseItem(
            -self.radius, -self.radius,
             self.radius * 2, self.radius * 2
        )
        circ.setPen(QPen(QColor("red"), 5))
        circ.setBrush(QBrush(Qt.NoBrush))

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setOffset(4, 4)
        shadow.setColor(QColor(0, 0, 0, 160))
        circ.setGraphicsEffect(shadow)

        self.addToGroup(circ)

    def _build_arrow(self):
        # placeholder triangle
        tri = QPolygonF([QPointF(0,0), QPointF(0,0), QPointF(0,0)])
        arrow = QGraphicsPolygonItem(tri)
        arrow.setBrush(QBrush(QColor("red")))
        arrow.setPen(QPen(QColor("red")))

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setOffset(3, 3)
        shadow.setColor(QColor(0, 0, 0, 160))
        arrow.setGraphicsEffect(shadow)

        arrow.setVisible(False)
        self.arrow = arrow
        self.addToGroup(arrow)

    def update_position(self, grid_x: int, grid_y: int):
        """Move the widget to the center of the given grid cell."""
        px = grid_x * GRID_SIZE
        py = grid_y * GRID_SIZE
        self.setPos(QPointF(px, py))

    def update_direction(self, code: int | None):
        """
        Show or hide the arrow based on numpad code.
        Valid codes: 1,2,3,4,6,7,8,9. Others hide the arrow.
        """
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
        # tip on circle
        tip = QPointF(ux * self.radius, uy * self.radius)
        # base center just inside
        bc = QPointF(
            ux * (self.radius - self.arrow_length),
            uy * (self.radius - self.arrow_length)
        )
        # perpendicular vector for width
        px_, py_ = -uy, ux
        half_w = self.arrow_width / 2

        left  = QPointF(bc.x() + px_ * half_w, bc.y() + py_ * half_w)
        right = QPointF(bc.x() - px_ * half_w, bc.y() - py_ * half_w)

        self.arrow.setPolygon(QPolygonF([tip, left, right]))
        self.arrow.setVisible(True)
