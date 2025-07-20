# ui/widgets/mapper/mapper_widget.py

from PySide6.QtGui import (
    QPainter,
)
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
)
from PySide6.QtCore import (
    QPointF,
    Qt,
)

from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.map_controller import MapController


class MapperWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Scene setup (do NOT assign to self.scene)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # View settings
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(Qt.black)

        # Zoom parameters
        self._zoom = 0

        # Map controller
        self.controller = MapController(self)

    def wheelEvent(self, event):
        """Zoom in/out with mouse wheel."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
            self._zoom += 1
        else:
            zoom_factor = zoom_out_factor
            self._zoom -= 1

        self.scale(zoom_factor, zoom_factor)

    def center_on_grid(self, grid_x: int, grid_y: int):
        """
        Center the viewport on the centre of the given grid cell.
        """
        px = grid_x * GRID_SIZE
        py = grid_y * GRID_SIZE
        self.centerOn(QPointF(px, py))

    def center_on_item(self, item):
        """
        Center the viewport on the given QGraphicsItem.
        """
        self.centerOn(item)

    def ensure_padding(self):
        """
        Expand sceneRect so the current itemsBoundingRect plus
        half the viewport always fits.
        """
        scene = self.scene()  # now calls QGraphicsView.scene()
        if scene is None:
            return

        items_rect = scene.itemsBoundingRect()
        vp = self.viewport().size()
        half_w = vp.width() / 2
        half_h = vp.height() / 2

        padded = items_rect.adjusted(
            -half_w, -half_h,
            half_w, half_h
        )
        scene.setSceneRect(padded)