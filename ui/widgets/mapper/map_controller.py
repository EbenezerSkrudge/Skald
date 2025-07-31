# ui/widgets/mapper/map_controller.py

import os
import pickle
from collections import Counter

from PySide6.QtCore import QObject, Signal, QPointF, QTimer
from PySide6.QtWidgets import QGraphicsScene

from ui.widgets.mapper.constants import GRID_SIZE, TEXT_TO_NUM, NUM_TO_DELTA
from ui.widgets.mapper.graphics.cardinal_direction_connector import CardinalDirectionConnector
from ui.widgets.mapper.graphics.non_cardinal_direction_connector import NonCardinalDirectionConnector
from ui.widgets.mapper.graphics.room_icon import RoomIcon
from ui.widgets.mapper.location_widget import LocationWidget
from ui.widgets.mapper.map_graph import MapGraph
from ui.widgets.mapper.utils import split_suffix


class MapController(QObject):
    mapUpdated = Signal()

    def __init__(self, mapper_widget, profile_path: str = None):
        super().__init__()
        self.map = mapper_widget
        self.profile_path = profile_path or os.path.expanduser("~/.skald/default")
        self.map_file_path = os.path.join(self.profile_path, "map.pickle")

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.save_map)

        self.global_graph = self._load_map() or MapGraph()
        self.local_graph = MapGraph()

        self._cur_hash = None
        self._prev_links = {}
        self._local_positions = {}
        self._local_icons = {}
        self.local_connectors = {}
        self._local_drawn_edges = set()
        self._local_border_arrows = []
        self._local_direction_tags = []
        self._marker = None

    def _load_map(self):
        if os.path.exists(self.map_file_path):
            try:
                with open(self.map_file_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading map: {e}")
        return None

    def save_map(self):
        try:
            os.makedirs(self.profile_path, exist_ok=True)
            temp_path = self.map_file_path + ".tmp"
            with open(temp_path, "wb") as f:
                pickle.dump(self.global_graph, f, protocol=pickle.HIGHEST_PROTOCOL) # type: ignore
            os.replace(temp_path, self.map_file_path)
        except Exception as e:
            print(f"Error saving map: {e}")

    def schedule_save(self):
        self._save_timer.start(1000)

    def on_room_info(self, info: dict):
        room_hash = info.get("hash")
        if not room_hash:
            return

        if self._cur_hash and self.global_graph.has_room(self._cur_hash):
            self._prev_links = dict(self.global_graph.get_room(self._cur_hash).links)
        else:
            self._prev_links.clear()

        self.global_graph.add_or_update_room(info, exit_types=info.get("exits", {}))

        prev_hash = self._cur_hash
        self._cur_hash = room_hash
        move_code = self._calculate_move_code(prev_hash, room_hash)

        self.build_local_area()
        self._update_marker(room_hash, move_code)
        self.render_local_graph()

        self.mapUpdated.emit()
        self.schedule_save()

    def _calculate_move_code(self, prev_hash, current_hash):
        if not prev_hash:
            return None
        direction = next((d for d, dst in self._prev_links.items() if dst == current_hash), None)
        return TEXT_TO_NUM.get(split_suffix(direction)[0]) if direction else None

    def _update_marker(self, room_hash, move_code):
        gx, gy = self._local_positions.get(room_hash, (0, 0))
        if not self._marker:
            self._marker = LocationWidget(gx, gy, direction_code=move_code)
            self.map.scene().addItem(self._marker)
        else:
            self._marker.update_position(gx, gy)
            self._marker.update_direction(move_code)

    def build_local_area(self):
        self.local_graph.clear()
        self._local_positions.clear()

        if not self._cur_hash or not self.global_graph.has_room(self._cur_hash):
            return

        self._local_positions = self.global_graph.layout_from_root(self._cur_hash)

        for h in self._local_positions:
            self.local_graph.add_room(self.global_graph.get_room(h))

        for a, b in self.global_graph.edges():
            if a in self._local_positions and b in self._local_positions:
                if not self.global_graph.is_border(a, b):
                    self.local_graph.connect_rooms(a, b)

    def render_local_graph(self):
        scene = self.map.scene()
        self._clear_scene_items(scene)
        self._draw_rooms(scene)
        self._draw_edges(scene)

    def _clear_scene_items(self, scene: QGraphicsScene):
        for item in self._local_border_arrows + self._local_direction_tags:
            scene.removeItem(item)
        for icon in self._local_icons.values():
            scene.removeItem(icon)
        for conn in self.local_connectors.values():
            scene.removeItem(conn)

        self._local_border_arrows.clear()
        self._local_direction_tags.clear()
        self._local_icons.clear()
        self.local_connectors.clear()
        self._local_drawn_edges.clear()

    def _draw_rooms(self, scene: QGraphicsScene):
        for room_hash, data in self.local_graph.nodes(data=True):
            room = data["room"]
            gx, gy = self._local_positions[room_hash]
            icon = RoomIcon(grid_x=gx, grid_y=gy, short_desc=room.desc, terrain=room.terrain)
            icon.reset_exit_vectors()
            scene.addItem(icon)
            self._local_icons[room_hash] = icon

            special_dirs = [d.lower() for d in room.links if d.lower() in ("in", "out", "up", "down")]
            if special_dirs:
                tag = NonCardinalDirectionConnector(icon, special_dirs)
                scene.addItem(tag)
                self._local_direction_tags.append(tag)

    def _draw_edges(self, scene: QGraphicsScene):
        for a, b in self.global_graph.edges():
            key = frozenset((a, b))
            if key in self._local_drawn_edges:
                continue

            conn = None

            attrs = self.global_graph[a][b]
            door_state = attrs.get("door")
            is_border = self.global_graph.is_border(a, b)

            icon_a = self._local_icons.get(a)
            icon_b = self._local_icons.get(b)

            if a in self._local_positions and b in self._local_positions:
                if not icon_a or not icon_b:
                    continue
                if self._is_multi_exit(a, b):
                    self._add_exit_vector(a, b)
                conn = CardinalDirectionConnector(icon_a, icon_b, door=door_state, border=is_border)
            elif is_border:
                conn = self._create_border_arrow(a, b, door_state)

            if conn:
                conn.add_to_scene(scene)
                self.local_connectors[key] = conn
                self._local_drawn_edges.add(key)

    def _is_multi_exit(self, room_hash_a, dest_hash):
        room = self.global_graph.get_room(room_hash_a)
        base_dirs = [split_suffix(d)[0] for d in room.links]
        counts = Counter(base_dirs)

        # Find direction string that links to the target room
        direction = next((d for d, dst in room.links.items() if dst == dest_hash), None)
        if not direction:
            return False  # Can't find a direction to that room

        base = split_suffix(direction)[0]
        return counts[base] > 1

    def _add_exit_vector(self, a, b):
        ax, ay = self._local_positions[a]
        bx, by = self._local_positions[b]
        dx, dy = bx - ax, by - ay
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length:
            self._local_icons[a].add_exit_vector(dx / length, dy / length)

    def _create_border_arrow(self, a, b, door_state):
        anchor = a if a in self._local_positions else b
        other = b if anchor == a else a
        icon_anchor = self._local_icons.get(anchor)
        if not icon_anchor:
            return None

        if other in self._local_positions:
            return CardinalDirectionConnector(icon_a=icon_anchor, icon_b=self._local_icons.get(other), door=door_state, border=True)

        dir_txt = next((d for d, dst in self.global_graph.get_room(anchor).links.items() if dst == other), "")
        dx, dy = NUM_TO_DELTA.get(TEXT_TO_NUM.get(split_suffix(dir_txt)[0], 8), (0, -1))
        pos = icon_anchor.scenePos()
        target_pos = QPointF(pos.x() + dx * GRID_SIZE, pos.y() + dy * GRID_SIZE)

        return CardinalDirectionConnector(icon_a=icon_anchor, target_pos=target_pos, door=door_state, border=True)
