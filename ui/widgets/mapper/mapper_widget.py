# ui/widgets/mapper/mapper_widget.py
from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QAction
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QMenu
)

from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.controller.map_controller import MapController
from ui.widgets.mapper.graphics.cardinal_direction_connector import CardinalDirectionConnector
from ui.widgets.mapper.graphics.room_icon import RoomIcon


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
        self.setStyleSheet("""
            QScrollBar:horizontal, QScrollBar:vertical {
                height: 1px;
                width: 1px;
                background: transparent;
            }
        """)

        self._zoom = 0
        self._shift_held = False

        self.controller = MapController(self, profile_path=profile_path)
        self._scene.controller = self.controller

    def contextMenuEvent(self, event):
        scene_pt = self.mapToScene(event.pos())
        items = self.scene().items(scene_pt)

        for it in items:
            # — 0) RoomIcon? —
            if isinstance(it, RoomIcon):
                room_icon = it

                room_hash = getattr(room_icon, "room_hash", None)
                if room_hash is None or room_hash not in self.controller.state.global_graph:
                    continue

                if room_hash is None:
                    continue

                menu = QMenu(self)
                delete_action = QAction("Delete Room", self)
                delete_action.triggered.connect(lambda _, h=room_hash: self._delete_room(h))
                menu.addAction(delete_action)
                menu.exec_(event.globalPos())
                return

            # — 1) normal ConnectorItem? —
            if isinstance(it, CardinalDirectionConnector):
                # find its edge in _local_connectors
                for edge, conn in self.controller.renderer.get_connectors().items():
                    if conn is it:
                        a_hash, b_hash = edge
                        break
                else:
                    continue

            else:
                continue  # not a connector we care about

            # Normalize ordering
            a, b = sorted((a_hash, b_hash))

            # Build menu
            is_border = self.controller.state.global_graph.is_border(a, b)
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
        self.controller.state.global_graph.set_border(a_hash, b_hash, flag)
        self.controller.render()

    def _delete_room(self, room_hash: str):
        graph = self.controller.state.global_graph

        if room_hash not in graph:
            return

        # Remove from graph
        graph.remove_node(room_hash)

        # Re-render map
        self.controller.render()
        self.controller.mapUpdated.emit()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom += 1 if factor > 1 else -1
        self.scale(factor, factor)

    def center_on_grid(self, gx, gy):
        self.centerOn(QPointF(gx * GRID_SIZE, gy * GRID_SIZE))

    def center_on_item(self, item):
        self.centerOn(item)

    def closeEvent(self, event):
        # let the controller unhook itself
        self._scene.controller.cleanup()
        super().closeEvent(event)
