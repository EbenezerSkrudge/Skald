# ui/widgets/mapper/connectors/connector_item.py

from PySide6.QtCore import QLineF
from PySide6.QtGui import Qt, QPen, QColor
from PySide6.QtWidgets import QGraphicsLineItem

from ui.widgets.mapper.constants import Z_CONNECTOR


class ConnectorItem(QGraphicsLineItem):
    """A basic line between two room icons that highlights on hover."""

    def __init__(self, icon_a, icon_b, color=Qt.darkGray, width=5):
        super().__init__()
        self.icon_a, self.icon_b = icon_a, icon_b
        self._normal_pen = QPen(QColor(color), width)
        self._hover_pen = QPen(Qt.cyan, width + 1)

        self.setPen(self._normal_pen)
        self.setZValue(Z_CONNECTOR)
        self.setAcceptHoverEvents(True)
        self.refresh()

    def refresh(self):
        self.setLine(QLineF(self.icon_a.scenePos(), self.icon_b.scenePos()))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)

    def add_to_scene(self, scene):
        scene.addItem(self)
