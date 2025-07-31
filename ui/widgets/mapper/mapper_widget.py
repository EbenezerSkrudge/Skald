# ui/widgets/mapper/mapper_widget.py
from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QAction
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QInputDialog, QMenu
)

from ui.widgets.mapper.graphics.cardinal_direction_connector import CardinalDirectionConnector
from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.map_controller import MapController


class MapperWidget(QGraphicsView):
    def __init__(self, parent=None, profile_path=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(Qt.black)

        self._zoom = 0
        self._shift_held = False

        self.controller = MapController(self, profile_path=profile_path)
        self._scene.controller = self.controller

    def contextMenuEvent(self, event):
        scene_pt = self.mapToScene(event.pos())
        items = self.scene().items(scene_pt)

        for it in items:
            # — 1) normal ConnectorItem? —
            if isinstance(it, CardinalDirectionConnector):
                # find its edge in _local_connectors
                for edge, conn in self.controller.local_connectors.items():
                    if conn is it:
                        a_hash, b_hash = edge
                        break
                else:
                    continue

            # # — 2) border arrow? —
            # elif isinstance(it, BorderConnectorItem):
            #     # read the attributes we stored on creation
            #     a_hash = getattr(it, "a_hash", None)
            #     b_hash = getattr(it, "b_hash", None)
            #     if not (a_hash and b_hash):
            #         continue

            else:
                continue  # not a connector we care about

            # Normalize ordering
            a, b = sorted((a_hash, b_hash))

            # Build menu
            is_border = self.controller.global_graph.is_border(a, b)
            menu = QMenu(self)
            label = "Remove Border" if is_border else "Set Border"
            action = QAction(label, self)
            # toggle to the opposite of current state
            action.triggered.connect(
                lambda _, x=a, y=b, f=not is_border: self._toggle_border(x, y, f)
            )
            menu.addAction(action)
            menu.exec_(event.globalPos())
            return

        # fallback if we didn’t hit a connector
        super().contextMenuEvent(event)

    @staticmethod
    def _get_connector_nodes(item) -> tuple[Optional[str], Optional[str]]:
        a_hash = getattr(item, "a_hash", None)
        b_hash = getattr(item, "b_hash", None)
        return a_hash, b_hash

    def _toggle_border(self, a_hash, b_hash, flag):
        self.controller.global_graph.set_border(a_hash, b_hash, flag)
        self.controller.build_local_area()
        self.controller.render_local_graph()
        self.controller.mapUpdated.emit()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom += 1 if factor > 1 else -1
        self.scale(factor, factor)

    def center_on_grid(self, gx, gy):
        self.centerOn(QPointF(gx * GRID_SIZE, gy * GRID_SIZE))

    def center_on_item(self, item):
        self.centerOn(item)

    def ensure_padding(self):
        if not self.scene():
            return
        rect = self.scene().itemsBoundingRect()
        half_w = self.viewport().width() / 2
        half_h = self.viewport().height() / 2
        self.scene().setSceneRect(rect.adjusted(-half_w, -half_h, half_w, half_h))

    def bulk_set_area(self):
        selected = [i for i in self.scene().selectedItems() if type(i).__name__ == "RoomIcon"]
        if not selected:
            return

        text, ok = QInputDialog.getText(self, "Set Area", f"Assign area to {len(selected)} selected rooms:")
        new_area = text.strip()
        if not ok or not new_area:
            return

        for icon in selected:
            for room_hash, data in self.controller.global_graph.nodes(data=True):
                if data["room"].icon is icon:
                    data["room"].area = new_area
                    break

        self.controller.mapUpdated.emit()

    def _set_drag_mode(self):
        self.setDragMode(QGraphicsView.RubberBandDrag if self._shift_held else QGraphicsView.ScrollHandDrag)

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
