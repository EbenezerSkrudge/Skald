# ui/widgets/mapper/mapper_widget.py

from PySide6.QtGui      import QPainter, QPen, QBrush, QColor, QLinearGradient
from PySide6.QtWidgets  import (QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem,
                                QGraphicsTextItem, QGraphicsRectItem)
from PySide6.QtCore     import Qt, QPointF

from ui.widgets.mapper.room_item import RoomItem
from ui.widgets.mapper.connector_item import ConnectorItem, DoorConnectorItem, NonCardinalDirectionTag


class MapperWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Scene setup
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # View settings
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(Qt.black)

        # Zoom parameters
        self._zoom = 0

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

    def render_test_room(self):
        room_size = 40
        spacing = 100

        # Base room
        forest_pos = QPointF(0, 0)
        forest = RoomItem(forest_pos, room_size, "Forest", QColor("#4CAF50"))
        self.scene.addItem(forest)

        # Town Gate (standard connector)
        town_pos = QPointF(forest_pos.x() + room_size + spacing, forest_pos.y())
        town_gate = RoomItem(town_pos, room_size, "Town Gate", QColor("#2196F3"))
        self.scene.addItem(town_gate)
        self.scene.addItem(ConnectorItem(forest, town_gate))

        # Cabin (open door)
        cabin_pos = QPointF(forest_pos.x(), forest_pos.y() - room_size - spacing)
        cabin = RoomItem(cabin_pos, room_size, "Cabin", QColor("#FFC107"))
        self.scene.addItem(cabin)
        DoorConnectorItem(forest, cabin, door_open=True).add_to_scene(self.scene)

        # Vault (closed door)
        vault_pos = QPointF(forest_pos.x(), forest_pos.y() + room_size + spacing)
        vault = RoomItem(vault_pos, room_size, "Vault", QColor("#9C27B0"))
        self.scene.addItem(vault)
        DoorConnectorItem(forest, vault, door_open=False).add_to_scene(self.scene)

        # Unexplored room
        unknown_pos = QPointF(forest_pos.x() + room_size + spacing, forest_pos.y() - spacing)
        unknown_room = RoomItem(unknown_pos, room_size, "???", QColor("#888"), explored=False)
        self.scene.addItem(unknown_room)
        self.scene.addItem(ConnectorItem(forest, unknown_room))

        # ─────────────────────────────────────────────
        # Non-cardinal directions
        # ─────────────────────────────────────────────

        # Up → Tree Canopy
        canopy_pos = QPointF(forest_pos.x(), forest_pos.y() - 2 * (room_size + spacing))
        canopy = RoomItem(canopy_pos, room_size, "Tree Canopy", QColor("#8BC34A"))
        self.scene.addItem(canopy)
        self.scene.addItem(ConnectorItem(forest, canopy))

        # Down → Cave
        cave_pos = QPointF(forest_pos.x(), forest_pos.y() + 2 * (room_size + spacing))
        cave = RoomItem(cave_pos, room_size, "Cave", QColor("#795548"))
        self.scene.addItem(cave)
        self.scene.addItem(ConnectorItem(forest, cave))

        # In → Tent
        tent_pos = QPointF(forest_pos.x() - 2 * (room_size + spacing), forest_pos.y())
        tent = RoomItem(tent_pos, room_size, "Tent", QColor("#FF5722"))
        self.scene.addItem(tent)
        self.scene.addItem(ConnectorItem(forest, tent))

        # Out → Trail
        trail_pos = QPointF(forest_pos.x() + 2 * (room_size + spacing), forest_pos.y())
        trail = RoomItem(trail_pos, room_size, "Trail", QColor("#CDDC39"))
        self.scene.addItem(trail)
        self.scene.addItem(ConnectorItem(forest, trail))

        self.scene.addItem(NonCardinalDirectionTag(tent, ["in"]))  # Tent has an 'out' exit back to Forest
        self.scene.addItem(NonCardinalDirectionTag(trail, ["in"]))  # Trail has an 'in' exit from Forest

        self.scene.addItem(NonCardinalDirectionTag(forest, ["out"]))

