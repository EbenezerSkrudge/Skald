from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QPen, QColor, QBrush,
    QPainterPath, QPainterPathStroker, QPolygonF
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsLineItem,
    QGraphicsRectItem, QGraphicsPolygonItem
)

from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE


class CardinalDirectionConnector(QGraphicsItem):
    # Static styles
    _COLOR_CONNECTOR = Qt.darkGray
    _COLOR_BORDER    = QColor("orange")
    _COLOR_HOVER     = Qt.cyan

    _PEN_CONNECTOR = QPen(_COLOR_CONNECTOR, 4)
    _PEN_BORDER    = QPen(_COLOR_BORDER, 4)

    _ARROW_SIZE = 8
    _ARROW_POLY = QPolygonF([
        QPointF(0, -_ARROW_SIZE),
        QPointF(-_ARROW_SIZE * 0.6, 0),
        QPointF(+_ARROW_SIZE * 0.6, 0),
    ])

    _DOOR_RECT = QRectF(-15, -5, 30, 10)
    _DOOR_STYLES = {
        "open":   (QBrush(QColor("lime")),   70),
        "closed": (QBrush(QColor("red")),    90),
    }

    def __init__(
        self,
        icon_a,
        icon_b=None,
        target_pos=None,
        door=None,
        border=False,
        shaft_length=16,
        line_width=4,
    ):
        super().__init__()

        self.icon_a     = icon_a
        self.icon_b     = icon_b
        self.target_pos = target_pos
        self.door_state = door
        self.border     = border

        self._pen_normal = self._PEN_BORDER if border else self._PEN_CONNECTOR
        self._pen_hover  = QPen(self._COLOR_HOVER, line_width + 1)

        self.setZValue(Z_CONNECTOR)
        self.setAcceptHoverEvents(True)

        self.line_item = QGraphicsLineItem(self)
        self.line_item.setPen(self._pen_normal)

        self.door_item = None
        if door in self._DOOR_STYLES:
            self.door_item = QGraphicsRectItem(self)
            self.door_item.setZValue(Z_ROOM_SHAPE)
            self.door_item.setTransformOriginPoint(0, 0)

        self.arrow_item = None
        if border:
            self.arrow_item = QGraphicsPolygonItem(self)
            self.arrow_item.setZValue(Z_CONNECTOR)
            self.arrow_item.setBrush(QBrush(self._COLOR_BORDER))
            self.arrow_item.setPen(self._pen_normal)
            self.arrow_item.setPolygon(self._ARROW_POLY)

        self.shaft_length = shaft_length
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

        if self.door_item and self.door_state in self._DOOR_STYLES:
            brush, rot_offset = self._DOOR_STYLES[self.door_state]
            self.door_item.setRect(self._DOOR_RECT)
            self.door_item.setBrush(brush)
            self.door_item.setRotation(angle + rot_offset)
            self.door_item.setPos(line.p2() if self.border else line.center())

        if self.arrow_item:
            if self.border and not self.door_state:
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
        if self.arrow_item:
            self.arrow_item.setPen(self._pen_hover)
        if self.door_item:
            self.door_item.setPen(self._pen_hover)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.line_item.setPen(self._pen_normal)
        if self.arrow_item:
            self.arrow_item.setPen(self._pen_normal)
        if self.door_item:
            self.door_item.setPen(QPen(Qt.NoPen))
        super().hoverLeaveEvent(event)

    def paint(self, *args):
        pass  # children handle their own painting