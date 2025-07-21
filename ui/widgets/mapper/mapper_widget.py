# ui/widgets/mapper/mapper_widget.py

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QLabel, QInputDialog
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.map_controller import MapController
from ui.widgets.mapper.room_item import RoomItem


class MapperWidget(QGraphicsView):
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

        # —– Controller hookup —–
        self.controller = MapController(self)
        self._scene.controller = self.controller

        # Whenever the map changes (new room, move, area-edit, delete), update label & filter
        self.controller.mapUpdated.connect(self._update_area_label)
        self.controller.mapUpdated.connect(self._filter_view_by_area)

        # —– Area label —–
        self.area_label = QLabel("", self)
        self.area_label.setStyleSheet(
            "color: white; background-color: rgba(0, 0, 0, 128); padding: 2px;"
        )
        self.area_label.move(10, 10)
        self.area_label.raise_()
        self.area_label.setMinimumWidth(100)

    def _update_area_label(self):
        cur = self.controller._cur_hash
        if cur and cur in self.controller.graph.nodes:
            area = self.controller.graph.nodes[cur].get("area", "")
            self.area_label.setText(f"Area: {area}")
        else:
            self.area_label.setText("")

    def _filter_view_by_area(self):
        # Only rooms/connectors in the current area remain visible
        cur = self.controller._cur_hash
        if not cur or cur not in self.controller.graph.nodes:
            return

        current_area = self.controller.graph.nodes[cur].get("area")

        # 1) Rooms
        for room_hash, (_, _, room_item) in self.controller._rooms.items():
            room_area = self.controller.graph.nodes[room_hash].get("area")
            room_item.setVisible(room_area == current_area)

        # 2) Connectors
        for edge, conn_item in self.controller._connectors.items():
            h1, h2 = tuple(edge)
            a1 = self.controller.graph.nodes[h1].get("area")
            a2 = self.controller.graph.nodes[h2].get("area")
            conn_item.setVisible(a1 == current_area and a2 == current_area)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom += 1 if factor > 1 else -1
        self.scale(factor, factor)

    def center_on_grid(self, gx: int, gy: int):
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
        selected = [
            item for item in self.scene().selectedItems()
            if isinstance(item, RoomItem)
        ]
        if not selected:
            return

        text, ok = QInputDialog.getText(self, "Set Area", f"Assign area to {len(selected)} selected rooms:")
        if ok and text.strip():
            for item in selected:
                hash_id = self.controller.find_room_hash(item)
                if hash_id:
                    self.controller.set_room_area(hash_id, text.strip())

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

