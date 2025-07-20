# ui/widgets/mapper/mapper_widget.py

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.map_controller import MapController


class MapperWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(Qt.black)

        self._zoom = 0
        self.controller = MapController(self)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom += 1 if factor > 1 else -1
        self.scale(factor, factor)

    def center_on_grid(self, gx: int, gy: int):
        self.centerOn(QPointF(gx * GRID_SIZE, gy * GRID_SIZE))

    def center_on_item(self, item):
        self.centerOn(item)

    def ensure_padding(self):
        if not (scene := self.scene()):
            return
        rect = scene.itemsBoundingRect()
        half_w, half_h = self.viewport().width() / 2, self.viewport().height() / 2
        scene.setSceneRect(rect.adjusted(-half_w, -half_h, half_w, half_h))
