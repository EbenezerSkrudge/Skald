# ui/widgets/mapper/mapper_widget.py

from PySide6.QtGui import QPainter, QAction
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QLabel, QInputDialog,
    QMenu
)
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.map_controller import MapController
from ui.widgets.mapper.connector_item import ConnectorItem, BorderConnectorItem, DoorBorderConnectorItem


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
        self._shift_held = False

        # —– Controller hookup —–
        self.controller = MapController(self)
        self._scene.controller = self.controller

        # —– Area label —–
        self.area_label = QLabel("", self)
        self.area_label.setStyleSheet(
            "color: white; background-color: rgba(0, 0, 0, 128); padding: 2px;"
        )
        self.area_label.move(10, 10)
        self.area_label.raise_()
        self.area_label.setMinimumWidth(100)

    def contextMenuEvent(self, event):
        scene_pt = self.mapToScene(event.pos())
        items    = self.scene().items(scene_pt)

        for raw in items:
            it = raw
            # unwrap if user clicked the line_item or rect_item
            parent = getattr(it, "parentItem", lambda: None)()
            if parent and isinstance(parent, DoorBorderConnectorItem):
                it = parent

            # 1) normal ConnectorItem (no border)
            if isinstance(it, ConnectorItem) and not isinstance(it, (BorderConnectorItem, DoorBorderConnectorItem)):
                # lookup edge in _local_connectors
                for (a, b), conn in self.controller._local_connectors.items():
                    if conn is it:
                        break
                else:
                    continue

            # 2) border or door‐border arrow?
            elif isinstance(it, (BorderConnectorItem, DoorBorderConnectorItem)):
                a = getattr(it, "a_hash", None)
                b = getattr(it, "b_hash", None)
                if not (a and b):
                    continue

            else:
                # not a clickable connector
                continue

            # normalize ordering
            a, b = sorted((a, b))

            # build the menu
            is_border = self.controller.global_graph.is_border(a, b)
            menu      = QMenu(self)
            if is_border:
                action = QAction("Remove Border", self)
                action.triggered.connect(
                    lambda _, x=a, y=b: self._toggle_border(x, y, False)
                )
            else:
                action = QAction("Set Border", self)
                action.triggered.connect(
                    lambda _, x=a, y=b: self._toggle_border(x, y, True)
                )
            menu.addAction(action)
            menu.exec_(event.globalPos())
            return

        super().contextMenuEvent(event)


    def _toggle_border(self, a_hash: str, b_hash: str, flag: bool):
        """
        Flip the 'border' flag on the given edge, then rebuild & redraw.
        """
        self.controller.global_graph.set_border(a_hash, b_hash, flag)
        self.controller.build_local_area()
        self.controller._render_local_graph()
        self.controller.mapUpdated.emit()

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