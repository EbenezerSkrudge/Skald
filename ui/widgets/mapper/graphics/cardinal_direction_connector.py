from typing import Optional

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QPen, QColor, QBrush,
    QPainterPath, QPainterPathStroker, QPolygonF
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsLineItem,
    QGraphicsRectItem, QGraphicsPolygonItem
)

from game.terrain import PATH_COLOUR, ROAD_COLOUR
from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE


class CardinalDirectionConnector(QGraphicsItem):
    # GMCP exit codes
    ROAD_EXIT    =  100
    PATH_EXIT    =  104
    DOOR_OPEN    =  101
    DOOR_CLOSED  = -101

    # Colors
    _COLOR_CONNECTOR = Qt.darkGray
    _COLOR_BORDER    = QColor("orange")
    _COLOR_HOVER     = Qt.cyan

    # Arrow geometry
    _ARROW_SIZE = 8
    _ARROW_POLY = QPolygonF([
        QPointF(0, -_ARROW_SIZE),
        QPointF(-_ARROW_SIZE * 0.6, 0),
        QPointF(+_ARROW_SIZE * 0.6, 0),
    ])

    # Door indicator rectangle
    _DOOR_RECT = QRectF(-15, -5, 30, 10)
    _DOOR_BRUSH = {
        DOOR_OPEN:   QBrush(QColor("lime")),
        DOOR_CLOSED: QBrush(QColor("red")),
    }
    _DOOR_ROT   = {
        DOOR_OPEN:   70,
        DOOR_CLOSED: 90,
    }

    def __init__(
        self,
        icon_a,
        icon_b=None,
        target_pos=None,
        border: bool           = False,
        shaft_length: float    = 16,
        line_width: float      = 4,
        exit_val: Optional[int] = None,
    ):
        super().__init__()
        self.icon_a      = icon_a
        self.icon_b      = icon_b
        self.target_pos  = target_pos
        self.border      = border
        self.exit_val    = int(exit_val) if exit_val is not None else None
        self.shaft_length = shaft_length

        # base line width
        lw = line_width
        if self.exit_val == self.ROAD_EXIT:
            lw *= 5
        elif self.exit_val == self.PATH_EXIT:
            lw *= 2.5

        base_color = self._COLOR_BORDER if border else self._COLOR_CONNECTOR
        self._pen_normal = QPen(base_color, lw)
        self._pen_hover  = QPen(self._COLOR_HOVER, lw + 1)

        # style exits
        if self.exit_val == self.PATH_EXIT:
            self._pen_normal.setColor(QColor(PATH_COLOUR))
        elif self.exit_val == self.ROAD_EXIT:
            self._pen_normal.setColor(QColor(ROAD_COLOUR))

        # graphics setup
        self.setZValue(Z_CONNECTOR)
        self.setAcceptHoverEvents(True)

        # connector line
        self.line_item = QGraphicsLineItem(self)
        self.line_item.setPen(self._pen_normal)

        # door indicator if open/closed
        self.door_item = None
        if self.exit_val in (self.DOOR_OPEN, self.DOOR_CLOSED):
            self.door_item = QGraphicsRectItem(self)
            self.door_item.setZValue(Z_ROOM_SHAPE)
            self.door_item.setTransformOriginPoint(0, 0)

        # border arrow
        self.arrow_item = None
        if border:
            self.arrow_item = QGraphicsPolygonItem(self)
            self.arrow_item.setZValue(Z_CONNECTOR)
            self.arrow_item.setBrush(QBrush(self._COLOR_BORDER))
            self.arrow_item.setPen(self._pen_normal)
            self.arrow_item.setPolygon(self._ARROW_POLY)

        self.refresh()

    def add_to_scene(self, scene):
        scene.addItem(self)

    def refresh(self):
        p1 = self.icon_a.scenePos()
        p2 = self.icon_b.scenePos() if self.icon_b else self.target_pos
        line = QLineF(p1, p2)
        angle = -line.angle()

        if self.border:
            line.setLength(line.length() / 2)

        self.line_item.setLine(line)
        self.line_item.setPen(self._pen_normal)

        # place door rectangle if needed
        ev = self.exit_val
        if self.door_item and ev in self._DOOR_BRUSH:
            brush   = self._DOOR_BRUSH[ev]
            rot_off = self._DOOR_ROT[ev]
            self.door_item.setRect(self._DOOR_RECT)
            self.door_item.setBrush(brush)
            self.door_item.setPen(QPen(Qt.NoPen))
            self.door_item.setRotation(angle + rot_off)
            pos = line.p2() if self.border else line.center()
            self.door_item.setPos(pos)

        # border arrow
        if self.arrow_item:
            if self.border and ev not in self._DOOR_BRUSH:
                self.arrow_item.setRotation(angle + 90)
                self.arrow_item.setPos(line.p2())
            else:
                self.arrow_item.setPolygon(QPolygonF())

    def boundingRect(self) -> QRectF:
        return self.childrenBoundingRect().adjusted(-6, -6, 6, 6)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        ln = self.line_item.line()
        path.moveTo(ln.p1())
        path.lineTo(ln.p2())

        stroker = QPainterPathStroker()
        stroker.setWidth(self._pen_normal.widthF() + 8)
        return stroker.createStroke(path)

    def hoverEnterEvent(self, event):
        self.line_item.setPen(self._pen_hover)
        if self.door_item:
            self.door_item.setPen(self._pen_hover)
        if self.arrow_item:
            self.arrow_item.setPen(self._pen_hover)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.line_item.setPen(self._pen_normal)
        if self.door_item:
            self.door_item.setPen(QPen(Qt.NoPen))
        if self.arrow_item:
            self.arrow_item.setPen(self._pen_normal)
        super().hoverLeaveEvent(event)

    def paint(self, *args):
        pass  # children paint themselves
