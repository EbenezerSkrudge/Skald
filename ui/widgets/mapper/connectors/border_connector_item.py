# ui/widgets/mapper/connectors/border_connector_item.py

from PySide6.QtCore import QPointF, QLineF
from PySide6.QtGui import Qt, QPen, QColor, QBrush, QPolygonF
from PySide6.QtWidgets import QGraphicsPolygonItem, QGraphicsLineItem

from ui.widgets.mapper.constants import Z_CONNECTOR
from ui.widgets.mapper.utils import midpoint


class BorderConnectorItem(QGraphicsPolygonItem):
    """An arrow indicating a border connection with hover highlight."""

    def __init__(self, icon_a, icon_b=None, target_pos=None, arrow_size=8, shaft_length=16, color=Qt.yellow):
        super().__init__()
        self.icon_a = icon_a
        self.icon_b = icon_b
        self.target_pos = target_pos
        self.arrow_size = arrow_size
        self.shaft_len = shaft_length

        self._normal_pen = QPen(QColor(color), 4)
        self._hover_pen = QPen(Qt.cyan, 5)

        self.setPen(self._normal_pen)
        self.setBrush(QBrush(QColor(color)))
        self.setZValue(Z_CONNECTOR)

        self.shaft = QGraphicsLineItem(self)
        self.shaft.setPen(self._normal_pen)
        self.shaft.setZValue(Z_CONNECTOR - 1)

        self._base_poly = QPolygonF([
            QPointF(0, -arrow_size),
            QPointF(-arrow_size * 0.6, 0),
            QPointF(+arrow_size * 0.6, 0),
        ])
        self.setPolygon(self._base_poly)

        self.setAcceptHoverEvents(True)
        self.shaft.setAcceptHoverEvents(True)
        self.refresh()

    def refresh(self):
        p1 = self.icon_a.scenePos()
        p2 = self.target_pos or self.icon_b.scenePos()
        mid = midpoint(p1, p2)
        angle = QLineF(p1, p2).angle()

        self.setRotation(-angle + 90)
        self.setPos(mid)
        self.shaft.setLine(QLineF(QPointF(0, 0), QPointF(0, self.shaft_len)))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)
        self.shaft.setPen(self._hover_pen)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)
        self.shaft.setPen(self._normal_pen)

    def add_to_scene(self, scene):
        scene.addItem(self)
