# ui/widgets/mapper/room_icon.py

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QPen, QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QGraphicsItem

from ui.widgets.mapper.constants import Z_ROOM_SHAPE, GRID_SIZE, ROOM_SIZE
from ui.widgets.mapper.utils import get_bold_font, get_terrain_color
from game.terrain import TERRAIN_TYPES


class RoomIcon(QGraphicsItem):
    _half = ROOM_SIZE / 2
    _pad  = 2

    # Pre-cache a QBrush for every valid terrain code (0–13)
    _terrain_brushes = {
        code: QBrush(get_terrain_color(name))
        for code, (name, _) in TERRAIN_TYPES.items()
    }
    # Fallback for illegal codes
    _default_brush = QBrush(get_terrain_color("none"))

    # Unexplored style
    _unexplored_brush = QBrush(QColor("#555555"))
    _border_pen       = QPen(Qt.darkGray, 1)
    _qmark_font       = get_bold_font(ROOM_SIZE * 0.5)
    _qmark_metrics    = QFontMetrics(_qmark_font)

    # Selection overlay style
    _sel_pen   = QPen(Qt.cyan, 2)
    _sel_brush = QBrush(QColor(0, 255, 255, 60))

    def __init__(
        self,
        grid_x: int,
        grid_y: int,
        short_desc: str,
        terrain: int
    ):
        super().__init__()
        self.grid_x  = grid_x
        self.grid_y  = grid_y
        self.terrain = terrain  # -1 means unexplored, 0–13 for known

        self.setToolTip(short_desc)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.RightButton)
        self.setZValue(Z_ROOM_SHAPE + 1)
        self.setPos(grid_x * GRID_SIZE, grid_y * GRID_SIZE)

    def boundingRect(self) -> QRectF:
        """
        Encompass the room shape (circle or square)
        plus selection padding.
        """
        total = ROOM_SIZE + self._pad * 2
        off   = -self._half - self._pad
        return QRectF(off, off, total, total)

    def paint(self, painter: QPainter, option, widget):
        # 1) Unexplored?
        if self.terrain == -1:
            # background circle
            painter.setBrush(self._unexplored_brush)
            painter.setPen(self._border_pen)
            painter.drawEllipse(-self._half,
                                -self._half,
                                 ROOM_SIZE,
                                 ROOM_SIZE)

            # question mark, centered
            painter.setFont(self._qmark_font)
            painter.setPen(Qt.gray)
            qm = "?"
            br = self._qmark_metrics.boundingRect(qm)
            # compute baseline x,y so the glyph's bounding rect is centered
            x = - (br.x() + br.width()  / 2)
            y = - (br.y() + br.height() / 2)
            painter.drawText(x, y, qm)

            # selection overlay (circle)
            if self.isSelected():
                painter.setPen(self._sel_pen)
                painter.setBrush(self._sel_brush)
                size = ROOM_SIZE + self._pad * 2
                off  = -self._half - self._pad
                painter.drawEllipse(off, off, size, size)
            return

        # 2) Known terrain: colored square
        brush = self._terrain_brushes.get(self.terrain,
                                          self._default_brush)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRect(-self._half,
                         -self._half,
                          ROOM_SIZE,
                          ROOM_SIZE)

        # 3) Selection overlay (square)
        if self.isSelected():
            painter.setPen(self._sel_pen)
            painter.setBrush(self._sel_brush)
            size = ROOM_SIZE + self._pad * 2
            off  = -self._half - self._pad
            painter.drawRect(off, off, size, size)