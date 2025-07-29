# ui/widgets/mapper/connectors/non_cardinal_direction_tag.py

from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsEllipseItem, QGraphicsLineItem

from ui.widgets.mapper.constants import Z_ROOM_ICON
from ui.widgets.mapper.utils import shorten_line, create_arrowhead


class NonCardinalDirectionTag(QGraphicsItemGroup):
    """Displays arrows for non-cardinal directions (in, out, up, down) around an icon."""

    def __init__(self, icon, directions: list[str]):
        super().__init__()
        self.setZValue(Z_ROOM_ICON)

        br = icon.boundingRect()
        center_scene = icon.mapToScene(br.center())
        cx, cy = center_scene.x(), center_scene.y()

        orange = QColor("orange")
        # TODO: Not needed if icon renders OK: arrow_pen = QPen(orange, 3)
        dash_pen = QPen(orange, 3)

        if any(d in directions for d in ("in", "out")):
            io_group = QGraphicsItemGroup(self)
            circ = QGraphicsEllipseItem(QRectF(-6, -6, 12, 12))
            circ.setPen(QPen(orange, 2))
            io_group.addToGroup(circ)

            for d in ("in", "out"):
                if d not in directions:
                    continue
                start, end = (
                    (QPointF(7, 7), QPointF(-2, -2)) if d == "in"
                    else (QPointF(0, 0), QPointF(9, 9))
                )
                se = shorten_line(start, end, 2)
                io_group.addToGroup(QGraphicsLineItem(start.x(), start.y(), se.x(), se.y()))
                io_group.addToGroup(create_arrowhead(start, end, orange))

            io_group.setPos(cx + 30, cy + 11)
            io_group.setZValue(Z_ROOM_ICON)

        if any(d in directions for d in ("up", "down")):
            ud_group = QGraphicsItemGroup(self)
            for x in (-5, 6):
                dash = QGraphicsLineItem(x - 1, 0, x, 0)
                dash.setPen(dash_pen)
                ud_group.addToGroup(dash)

            for d in ("up", "down"):
                if d not in directions:
                    continue
                y = 6
                start, end = (
                    (QPointF(0, y), QPointF(0, -y - 2)) if d == "up"
                    else (QPointF(0, -y), QPointF(0, y + 2))
                )
                se = shorten_line(start, end, 2)
                ud_group.addToGroup(QGraphicsLineItem(start.x(), start.y(), se.x(), se.y()))
                ud_group.addToGroup(create_arrowhead(start, end, orange))

            ud_group.setPos(cx + 31, cy - 12)
            ud_group.setZValue(Z_ROOM_ICON)
