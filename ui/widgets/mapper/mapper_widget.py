# ui/widgets/mapper/mapper_widget.py

from PySide6.QtGui import QPainter, QAction
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QLabel, QInputDialog, QMenu
)
from PySide6.QtCore import QPointF, Qt

from ui.widgets.mapper.constants import GRID_SIZE
from ui.widgets.mapper.map_controller import MapController
from ui.widgets.mapper.connector_item import (
    ConnectorItem, BorderConnectorItem, DoorBorderConnectorItem
)


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
        self._shift_held = False

        self.controller = MapController(self)
        self._scene.controller = self.controller

        self._setup_area_label()

    def _setup_area_label(self):
        self.area_label = QLabel("", self)
        self.area_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 128); padding: 2px;")
        self.area_label.move(10, 10)
        self.area_label.raise_()
        self.area_label.setMinimumWidth(100)

    def contextMenuEvent(self, event):
        item = self._get_connector_item(self.mapToScene(event.pos()))
        if not item:
            return super().contextMenuEvent(event)

        a, b = self._get_connector_nodes(item)
        if not (a and b):
            return

        a, b = sorted((a, b))
        is_border = self.controller.global_graph.is_border(a, b)
        label = "Remove Border" if is_border else "Set Border"
        action = QAction(label, self)
        action.triggered.connect(lambda _, x=a, y=b, f=not is_border: self._toggle_border(x, y, f))

        menu = QMenu(self)
        menu.addAction(action)
        menu.exec_(event.globalPos())

    def _get_connector_item(self, scene_pos):
        for item in self.scene().items(scene_pos):
            parent = getattr(item, "parentItem", lambda: None)()
            connector = parent if isinstance(parent, DoorBorderConnectorItem) else item
            if isinstance(connector, ConnectorItem):
                return connector
        return None

    def _get_connector_nodes(self, item):
        if isinstance(item, (BorderConnectorItem, DoorBorderConnectorItem)):
            return item.a_hash, item.b_hash
        for (a, b), conn in self.controller._local_connectors.items():
            if conn is item:
                return a, b
        return None, None

    def _toggle_border(self, a_hash, b_hash, flag):
        self.controller.global_graph.set_border(a_hash, b_hash, flag)
        self.controller.build_local_area()
        self.controller._render_local_graph()
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
