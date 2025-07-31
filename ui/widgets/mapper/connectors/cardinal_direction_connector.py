from PySide6.QtCore import (
    QLineF, QPointF, QRectF, Qt
)
from PySide6.QtGui import (
    QPen, QColor, QBrush, QPainterPath, QPainterPathStroker, QPolygonF
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem, QGraphicsPolygonItem
)

from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE


class CardinalDirectionConnector(QGraphicsItem):
    # Colors & pens
    _CONNECTOR_COLOUR = Qt.darkGray
    _HOVER_COLOUR = Qt.cyan
    _BORDER_COLOUR = QColor("orange")

    _CONNECTOR_PEN = QPen(_CONNECTOR_COLOUR, 4)
    _BORDER_PEN = QPen(_BORDER_COLOUR, 4)

    # Arrow template (size = 8px)
    _BASE_ARROW_SIZE = 8
    _BASE_ARROW_POLY = QPolygonF([
        QPointF(0, -_BASE_ARROW_SIZE),
        QPointF(-_BASE_ARROW_SIZE * 0.6, 0),
        QPointF(+_BASE_ARROW_SIZE * 0.6, 0),
    ])

    # Door templates
    _DOOR_WIDTH = 30
    _DOOR_HEIGHT = 10
    _DOOR_RECT = QRectF(-_DOOR_WIDTH / 2,
                        -_DOOR_HEIGHT / 2,
                        _DOOR_WIDTH,
                        _DOOR_HEIGHT)
    _DOOR_BRUSHES = {
        "open": QBrush(QColor("lime")),
        "closed": QBrush(QColor("red")),
    }
    _DOOR_ROTATIONS = {
        "open": 70,
        "closed": 90,
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

        self.icon_a = icon_a
        self.icon_b = icon_b
        self.target_pos = target_pos
        self.door_state = door  # None, "open", or "closed"
        self.border = border

        # Pens
        self._normal_pen = (
            self._BORDER_PEN if border
            else self._CONNECTOR_PEN
        )
        self._hover_pen = QPen(self._HOVER_COLOUR,
                               line_width + 1)

        # Z‐order + hover
        self.setZValue(Z_CONNECTOR)
        self.setAcceptHoverEvents(True)

        # Main line
        self.line_item = QGraphicsLineItem(self)
        self.line_item.setPen(self._normal_pen)

        # Door (optional)
        self.door_item = None
        if door is not None:
            self.door_item = QGraphicsRectItem(self)
            self.door_item.setZValue(Z_ROOM_SHAPE)
            # pivot about its center
            self.door_item.setTransformOriginPoint(0, 0)

        # Arrow (optional, border only)
        self.arrow_item = None
        if border:
            self.arrow_item = QGraphicsPolygonItem(self)
            self.arrow_item.setZValue(Z_CONNECTOR)
            self.arrow_item.setBrush(QBrush(self._BORDER_COLOUR))
            self.arrow_item.setPen(self._normal_pen)
            self.arrow_item.setPolygon(self._BASE_ARROW_POLY)

        # Initial layout
        self.shaft_length = shaft_length
        self.refresh()

    def add_to_scene(self, scene):
        """Back‐compatibility convenience."""
        scene.addItem(self)

    def refresh(self):
        # endpoints & angle
        p1 = self.icon_a.scenePos()
        p2 = self.icon_b.scenePos() if self.icon_b else self.target_pos
        line = QLineF(p1, p2)
        length = line.length()
        angle = -line.angle()

        # halve for border‐connectors
        if self.border:
            line.setLength(length / 2)

        # update line
        self.line_item.setLine(line)

        # update door
        if self.door_item and self.door_state in self._DOOR_ROTATIONS:
            pos = (line.p2() if self.border
                   else line.center())
            rot_off = self._DOOR_ROTATIONS[self.door_state]
            brush = self._DOOR_BRUSHES[self.door_state]

            # apply templates
            self.door_item.setRect(self._DOOR_RECT)
            self.door_item.setBrush(brush)

            # rotate around center, then position
            self.door_item.setRotation(angle + rot_off)
            self.door_item.setPos(pos)

        # update arrow
        if self.arrow_item:
            if self.border and not self.door_state:
                self.arrow_item.setRotation(angle + 90)
                self.arrow_item.setPos(line.p2())
            else:
                # hide it by clearing polygon
                self.arrow_item.setPolygon(QPolygonF())

    def boundingRect(self) -> QRectF:
        rect = self.childrenBoundingRect()
        return rect.adjusted(-6, -6, 6, 6)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        ln = self.line_item.line()
        path.moveTo(ln.p1())
        path.lineTo(ln.p2())

        stroker = QPainterPathStroker()
        stroker.setWidth(self._normal_pen.widthF() + 8)
        return stroker.createStroke(path)

    def hoverEnterEvent(self, event):
        self.line_item.setPen(self._hover_pen)
        if self.arrow_item:
            self.arrow_item.setPen(self._hover_pen)
        if self.door_item:
            self.door_item.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.line_item.setPen(self._normal_pen)
        if self.arrow_item:
            self.arrow_item.setPen(self._normal_pen)
        if self.door_item:
            self.door_item.setPen(QPen(Qt.NoPen))
        super().hoverLeaveEvent(event)

    def paint(self, *args):
        # children paint themselves
        pass
