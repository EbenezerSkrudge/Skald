# ui/widgets/mapper/mapper_widget.py

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QLabel, QInputDialog
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.map_controller import MapController


class MapperWidget(QGraphicsView):
    """
    Displays the local submap (icons + connectors) managed by MapController.
    No longer filters a global map by area; instead, MapController builds
    and renders only the local subgraph on each update.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # —– Scene setup —–
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(Qt.black)

        self._zoom = 0
        self._shift_held = False

        # —– Controller hookup —–
        self.controller = MapController(self)
        self._scene.controller = self.controller

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom += 1 if factor > 1 else -1
        self.scale(factor, factor)

    def center_on_grid(self, gx: int, gy: int):
        # Center the view on a grid coordinate
        self.centerOn(QPointF(gx * GRID_SIZE, gy * GRID_SIZE))

    def center_on_item(self, item):
        self.centerOn(item)

    def ensure_padding(self):
        scene = self.scene()
        if not scene:
            return
        rect = scene.itemsBoundingRect()
        half_w = self.viewport().width() / 2
        half_h = self.viewport().height() / 2
        scene.setSceneRect(rect.adjusted(-half_w, -half_h, half_w, half_h))

    def bulk_set_area(self):
        # Allows assigning a new area name to one or more selected rooms
        selected = [
            item for item in self.scene().selectedItems()
            if type(item).__name__ == "RoomIcon"
        ]
        if not selected:
            return

        text, ok = QInputDialog.getText(
            self,
            "Set Area",
            f"Assign area to {len(selected)} selected rooms:"
        )
        if not ok or not text.strip():
            return
        new_area = text.strip()

        # Update each Room's area via the global graph
        for icon in selected:
            for room_hash, data in self.controller.global_graph.nodes(data=True):
                if data["room"].icon is icon:
                    data["room"].area = new_area
                    break

        # Rebuild/redraw local submap and update label
        self.controller.mapUpdated.emit()

    def _set_drag_mode(self):
        if self._shift_held:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self._shift_held = True
            self._set_drag_mode()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self._shift_held = False
            self._set_drag_mode()
        super().keyReleaseEvent(event)