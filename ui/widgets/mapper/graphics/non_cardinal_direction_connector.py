# ui/widgets/mapper/graphics/non_cardinal_direction_connector.py

from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsEllipseItem, QGraphicsLineItem

from ui.widgets.mapper.constants import Z_ROOM_ICON
from ui.widgets.mapper.utils import shorten_line, create_arrowhead


class NonCardinalDirectionConnector(QGraphicsItemGroup):
    """Displays arrows for non-cardinal directions (in, out, up, down) around an icon."""

    _COLOR = QColor("orange")
    _PEN_LINE = QPen(_COLOR, 3)
    _PEN_CIRCLE = QPen(_COLOR, 2)

    def __init__(self, icon, directions: list[str]):
        super().__init__()
        self.setZValue(Z_ROOM_ICON)

        center = icon.mapToScene(icon.boundingRect().center())
        cx, cy = center.x(), center.y()

        if set(directions) & {"in", "out"}:
            self._add_in_out_group(cx, cy, directions)

        if set(directions) & {"up", "down"}:
            self._add_up_down_group(cx, cy, directions)

    def _add_in_out_group(self, cx, cy, directions):
        circle = QGraphicsEllipseItem(QRectF(cx + 24, cy + 5, 12, 12))
        circle.setPen(self._PEN_CIRCLE)
        self.addToGroup(circle)

        arrow_defs = {
            "in":  (QPointF(cx + 37, cy + 18), QPointF(cx + 28, cy + 9)),
            "out": (QPointF(cx + 30, cy + 11), QPointF(cx + 39, cy + 20)),
        }

        for d in ("in", "out"):
            if d not in directions:
                continue
            start, end = arrow_defs[d]
            se = shorten_line(start, end, 2)
            shaft = QGraphicsLineItem(start.x(), start.y(), se.x(), se.y())
            shaft.setPen(self._PEN_LINE)
            self.addToGroup(shaft)
            self.addToGroup(create_arrowhead(start, end, self._COLOR))

    def _add_up_down_group(self, cx, cy, directions):
        base_x = cx + 29
        base_y = cy - 12

        # Add horizontal dashes
        for x_offset in (-5, 6):
            x1 = base_x + x_offset - 1
            x2 = base_x + x_offset
            dash = QGraphicsLineItem(x1, base_y, x2, base_y)
            dash.setPen(self._PEN_LINE)
            self.addToGroup(dash)

        # Arrow definitions relative to local origin
        arrow_defs = {
            "up": (QPointF(0, 6), QPointF(0, -8)),
            "down": (QPointF(0, -6), QPointF(0, 8)),
        }

        for d in ("up", "down"):
            if d not in directions:
                continue
            local_start, local_end = arrow_defs[d]
            local_se = shorten_line(local_start, local_end, 2)

            # Offset to scene position
            start = QPointF(base_x + local_start.x(), base_y + local_start.y())
            se = QPointF(base_x + local_se.x(), base_y + local_se.y())
            end = QPointF(base_x + local_end.x(), base_y + local_end.y())

            shaft = QGraphicsLineItem(start.x(), start.y(), se.x(), se.y())
            shaft.setPen(self._PEN_LINE)
            self.addToGroup(shaft)
            self.addToGroup(create_arrowhead(start, end, self._COLOR))
