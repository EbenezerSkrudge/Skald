# ui/widgets/mapper/controller/map_renderer.py

from collections import Counter
from PySide6.QtCore import QRectF, QPointF
from PySide6.QtWidgets import QGraphicsRectItem

from ui.widgets.mapper.constants import GRID_SIZE, TEXT_TO_NUM, NUM_TO_DELTA
from ui.widgets.mapper.graphics.room_icon import RoomIcon
from ui.widgets.mapper.graphics.cardinal_direction_connector import CardinalDirectionConnector
from ui.widgets.mapper.graphics.non_cardinal_direction_connector import NonCardinalDirectionConnector
from ui.widgets.mapper.location_widget import LocationWidget
from ui.widgets.mapper.utils import split_suffix


class MapRenderer:
    ANCHOR_DISTANCE = 50000  # You can tune this or compute dynamically

    def __init__(self, map_view, state):
        self.map = map_view
        self.state = state
        self._marker = None
        self._icons = {}
        self._connectors = {}
        self._drawn_edges = set()
        self._tags = []
        self._borders = []
        self._anchors = []

    def render(self, root_hash, positions):
        scene = self.map.scene()

        self._clear_scene()
        if not root_hash:
            return

        view_rect = self._get_view_rect()

        # 🧱 Add room icons
        for room_hash, (gx, gy) in positions.items():
            icon_rect = QRectF(gx * GRID_SIZE, gy * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            if view_rect.intersects(icon_rect):
                self._add_icon(scene, room_hash, gx, gy)

        # 🔗 Add connectors
        for a, b in self.state.global_graph.edges():
            key = frozenset((a, b))
            if key in self._drawn_edges:
                continue

            icon_a, icon_b = self._icons.get(a), self._icons.get(b)
            attrs = self.state.global_graph[a][b]
            is_border = self.state.global_graph.is_border(a, b)
            exit_val = attrs.get("exit_val")
            conn = None

            if icon_a and icon_b:
                if view_rect.intersects(
                        QRectF(icon_a.scenePos(), icon_b.scenePos()).normalized().adjusted(-1, -1, 1, 1)):
                    if self._is_multi_exit(a, b):
                        self._add_exit_vector(a, b, positions)
                    conn = CardinalDirectionConnector(icon_a, icon_b, border=is_border, exit_val=exit_val)
            elif is_border and (icon := icon_a or icon_b):
                if view_rect.intersects(icon.sceneBoundingRect()):
                    conn = self._create_border_arrow(a, b, positions)

            if conn:
                conn.add_to_scene(scene)
                self._connectors[key] = conn
                self._drawn_edges.add(key)

        self._add_pan_anchors(positions)

    def update_marker(self, room_hash, move_code):
        x, y = self.state.global_graph.layout_from_root(room_hash).get(room_hash, (0, 0))
        if self._marker:
            self._marker.update_position(x, y)
            self._marker.update_direction(move_code)
        else:
            self._marker = LocationWidget(x, y, direction_code=move_code)
            self.map.scene().addItem(self._marker)

        self.map.centerOn(self._marker)

    def get_connectors(self):
        return self._connectors

    def _get_view_rect(self):
        return self.map.mapToScene(self.map.viewport().rect()).boundingRect().adjusted(-GRID_SIZE, -GRID_SIZE, GRID_SIZE, GRID_SIZE)

    def _clear_scene(self):
        scene = self.map.scene()
        for group in (self._icons.values(), self._connectors.values(), self._tags, self._borders, self._anchors):
            for item in group:
                scene.removeItem(item)

        self._icons.clear()
        self._connectors.clear()
        self._tags.clear()
        self._borders.clear()
        self._drawn_edges.clear()
        self._anchors.clear()

    def _add_icon(self, scene, room_hash, gx, gy):
        room = self.state.global_graph.get_room(room_hash)
        icon = RoomIcon(room_hash, gx, gy, room.desc, room.terrain)
        icon.reset_exit_vectors()
        scene.addItem(icon)
        self._icons[room_hash] = icon

        tags = [d.lower() for d in room.links if d.lower() in ("in", "out", "up", "down")]
        if tags:
            tag = NonCardinalDirectionConnector(icon, tags)
            scene.addItem(tag)
            self._tags.append(tag)

    def _is_multi_exit(self, a, b):
        room = self.state.global_graph.get_room(a)
        directions = [split_suffix(d)[0] for d in room.links]
        count = Counter(directions)
        direction = next((d for d, dst in room.links.items() if dst == b), None)
        return count[split_suffix(direction)[0]] > 1 if direction else False

    def _add_exit_vector(self, a, b, positions):
        ax, ay = positions[a]
        bx, by = positions[b]
        dx, dy = bx - ax, by - ay
        length = (dx**2 + dy**2)**0.5
        if length:
            self._icons[a].add_exit_vector(dx / length, dy / length)

    def _create_border_arrow(self, a, b, positions):
        anchor = a if a in positions else b
        other = b if anchor == a else a
        icon = self._icons.get(anchor)
        if not icon:
            return None

        attrs = self.state.global_graph[a][b]
        exit_val = attrs.get("exit_val")

        if other in self._icons:
            return CardinalDirectionConnector(icon, self._icons[other], border=True, exit_val=exit_val)

        dir_txt = next((d for d, dst in self.state.global_graph.get_room(anchor).links.items() if dst == other), "")
        code = TEXT_TO_NUM.get(split_suffix(dir_txt)[0], 8)
        dx, dy = NUM_TO_DELTA.get(code, (0, -1))
        target = icon.scenePos() + QPointF(dx * GRID_SIZE, dy * GRID_SIZE)

        return CardinalDirectionConnector(icon, target_pos=target, border=True, exit_val=exit_val)

    def _add_pan_anchors(self, positions):
        scene = self.map.scene()
        size = 1
        distance = self.ANCHOR_DISTANCE

        anchors = [
            QPointF(-distance, -distance),
            QPointF(distance, -distance),
            QPointF(-distance, distance),
            QPointF(distance, distance),
        ]

        for pos in anchors:
            anchor = QGraphicsRectItem(pos.x(), pos.y(), size, size)
            anchor.setVisible(False)
            anchor.setFlag(QGraphicsRectItem.ItemIgnoresTransformations, True)
            scene.addItem(anchor)
            self._anchors.append(anchor)
