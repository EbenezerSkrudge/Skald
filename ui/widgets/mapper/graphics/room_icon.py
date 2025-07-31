from typing import List, Tuple, Optional
from math import sqrt

from PySide6.QtCore import QRectF, Qt, QPointF
from PySide6.QtGui import (
    QBrush, QPen, QColor, QFontMetrics, QPainter
)
from PySide6.QtWidgets import (
    QGraphicsItem, QStyleOptionGraphicsItem, QWidget
)

from ui.widgets.mapper.constants import Z_ROOM_SHAPE, GRID_SIZE, ROOM_SIZE
from ui.widgets.mapper.utils import get_bold_font, get_terrain_color
from game.terrain import TERRAIN_TYPES


class RoomIcon(QGraphicsItem):
    _HALF = ROOM_SIZE / 2
    _PAD = 2
    _DIAMOND_SIZE = 8
    _DIAMOND_OFFSET = _HALF + _DIAMOND_SIZE

    # Brushes and pens
    _terrain_brushes = {
        code: QBrush(get_terrain_color(name))
        for code, (name, _) in TERRAIN_TYPES.items()
    }
    _default_brush = QBrush(get_terrain_color("none"))
    _unexplored_brush = QBrush(QColor("#555555"))

    _border_pen = QPen(Qt.darkGray, 1)
    _sel_pen = QPen(Qt.cyan, 2)
    _sel_brush = QBrush(QColor(0, 255, 255, 60))

    _qmark_font = get_bold_font(ROOM_SIZE * 0.5)
    _qmark_metrics = QFontMetrics(_qmark_font)

    def __init__(self, grid_x: int, grid_y: int, short_desc: str, terrain: int):
        super().__init__()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.terrain = terrain  # -1 = unexplored, 0–13 = known
        self.exit_vectors: List[Tuple[float, float]] = []

        self.setToolTip(short_desc)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.RightButton)
        self.setZValue(Z_ROOM_SHAPE + 1)
        self.setPos(grid_x * GRID_SIZE, grid_y * GRID_SIZE)

    def boundingRect(self) -> QRectF:
        size = ROOM_SIZE + self._PAD * 2
        offset = -self._HALF - self._PAD
        return QRectF(offset, offset, size, size)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        if self.terrain == -1:
            self._paint_unexplored(painter)
        else:
            self._paint_terrain(painter)

        if self.isSelected():
            self._paint_selection_overlay(painter)

        if self.exit_vectors:
            self._paint_exit_diamond(painter)

    def _paint_unexplored(self, painter: QPainter):
        painter.setBrush(self._unexplored_brush)
        painter.setPen(self._border_pen)
        painter.drawEllipse(round(-self._HALF), round(-self._HALF), ROOM_SIZE, ROOM_SIZE)

        painter.setFont(self._qmark_font)
        painter.setPen(Qt.gray)
        qm = "?"
        br = self._qmark_metrics.boundingRect(qm)
        x = - (br.x() + br.width() / 2)
        y = - (br.y() + br.height() / 2)
        painter.drawText(round(x), round(y), qm)

    def _paint_terrain(self, painter: QPainter):
        brush = self._terrain_brushes.get(self.terrain, self._default_brush)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRect(round(-self._HALF), round(-self._HALF), ROOM_SIZE, ROOM_SIZE)

    def _paint_selection_overlay(self, painter: QPainter):
        painter.setPen(self._sel_pen)
        painter.setBrush(self._sel_brush)
        size = ROOM_SIZE + self._PAD * 2
        offset = -self._HALF - self._PAD
        if self.terrain == -1:
            painter.drawEllipse(round(offset), round(offset), size, size)
        else:
            painter.drawRect(round(offset), round(offset), size, size)

    def _paint_exit_diamond(self, painter: QPainter):
        dx, dy = self.primary_exit_unit_vector()
        cx = dx * self._DIAMOND_OFFSET
        cy = dy * self._DIAMOND_OFFSET

        painter.setBrush(QColor("orange"))
        painter.setPen(Qt.NoPen)
        s = self._DIAMOND_SIZE
        points = [
            QPointF(cx, cy - s),
            QPointF(cx + s, cy),
            QPointF(cx, cy + s),
            QPointF(cx - s, cy)
        ]
        painter.drawPolygon(points)

    # ─── Multi-exit support ─────────────────────────────────────────────

    def reset_exit_vectors(self) -> None:
        self.exit_vectors.clear()

    def add_exit_vector(self, ux: float, uy: float) -> None:
        self.exit_vectors.append((ux, uy))

    def primary_exit_unit_vector(self) -> Tuple[float, float]:
        if not self.exit_vectors:
            return 0.0, -1.0

        sx = sum(x for x, _ in self.exit_vectors)
        sy = sum(y for _, y in self.exit_vectors)
        length = sqrt(sx * sx + sy * sy)
        return (sx / length, sy / length) if length else (0.0, -1.0)