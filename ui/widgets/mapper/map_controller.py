# ui/widgets/mapper/map_controller.py

import os
import pickle

from PySide6.QtCore import QObject, Signal, QPointF
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGraphicsScene

from ui.widgets.mapper.graphics.non_cardinal_direction_connector import NonCardinalDirectionConnector
from ui.widgets.mapper.graphics.cardinal_direction_connector import CardinalDirectionConnector
from ui.widgets.mapper.constants import GRID_SIZE, TEXT_TO_NUM, NUM_TO_DELTA
from ui.widgets.mapper.location_widget import LocationWidget
from ui.widgets.mapper.map_graph import MapGraph
from ui.widgets.mapper.graphics.room_icon import RoomIcon
from ui.widgets.mapper.utils import split_suffix


class MapController(QObject):
    mapUpdated = Signal()

    def __init__(self, mapper_widget, profile_path: str = None):
        super().__init__()
        self.map = mapper_widget
        self.profile_path = profile_path or os.path.expanduser("~/.skald/default")
        self.map_file_path = os.path.join(self.profile_path, "map.pickle")

        # Debounce timer for saving
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.save_map)

        self.global_graph = self._load_map() or MapGraph()
        self.local_graph = MapGraph()
        self._local_positions = {}
        self._cur_hash = None

        self._local_icons = {}
        self.local_connectors = {}
        self._local_drawn_edges = set()
        self._local_border_arrows = []
        self._local_direction_tags = []
        self._marker = None
        self._prev_links = {}

    def save_map(self):
        try:
            os.makedirs(self.profile_path, exist_ok=True)
            temp_path = self.map_file_path + ".tmp"
            with open(temp_path, "wb") as f:
                pickle.dump(self.global_graph, f, protocol=pickle.HIGHEST_PROTOCOL)  # type: ignore
            os.replace(temp_path, self.map_file_path)  # Atomic on most platforms
        except Exception as e:
            print(f"Error saving map: {e}")

    def _load_map(self) -> MapGraph | None:
        print(self.map_file_path)
        if os.path.exists(self.map_file_path):
            try:
                with open(self.map_file_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading map: {e}")
        return None

    def on_room_info(self, info: dict):
        room_hash = info.get("hash")
        if not room_hash:
            return

        if self._cur_hash and self.global_graph.has_room(self._cur_hash):
            self._prev_links = dict(self.global_graph.get_room(self._cur_hash).links)
        else:
            self._prev_links.clear()

        exits = info.get("exits", {})
        self.global_graph.add_or_update_room(info, exit_types=exits)

        prev_hash = self._cur_hash
        self._cur_hash = room_hash
        move_code = self._calculate_move_code(prev_hash, room_hash)

        self.build_local_area()

        gx, gy = self._local_positions.get(room_hash, (0, 0))
        if not self._marker:
            self._marker = LocationWidget(gx, gy, direction_code=move_code)
            self.map.scene().addItem(self._marker)
        else:
            self._marker.update_position(gx, gy)
            self._marker.update_direction(move_code)

        self.render_local_graph()
        self.mapUpdated.emit()

        self.schedule_save()

    def schedule_save(self):
        self._save_timer.start(1000)  # Save 1s after last move

    def _calculate_move_code(self, prev_hash, current_hash):
        if not prev_hash:
            return None
        movement_direction = next((d for d, dest in self._prev_links.items() if dest == current_hash), None)
        if movement_direction:
            base, _ = split_suffix(movement_direction)
            return TEXT_TO_NUM.get(base)
        return None

    def build_local_area(self) -> MapGraph:
        self.local_graph = MapGraph()
        self._local_positions.clear()

        if not self._cur_hash or not self.global_graph.has_room(self._cur_hash):
            return self.local_graph

        self._local_positions = self.global_graph.layout_from_root(self._cur_hash)
        for h in self._local_positions:
            self.local_graph.add_room(self.global_graph.get_room(h))

        for a, b in self.global_graph.edges():
            if a in self._local_positions and b in self._local_positions:
                if not self.global_graph.is_border(a, b):
                    self.local_graph.connect_rooms(a, b)

        return self.local_graph

    def render_local_graph(self):
        scene = self.map.scene()
        self._clear_scene_items(scene)
        self._draw_rooms(scene)
        # self._draw_connectors(scene)
        # self._draw_borders(scene)
        self._draw_edges(scene)

    def _clear_scene_items(self, scene: QGraphicsScene):
        # The clear logic remains unchanged but deletes unified graphics
        for item in (*self._local_border_arrows, *self._local_direction_tags):
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
            scene.addItem(icon)
            self._local_icons[room_hash] = icon

            tags = [d.lower() for d in room.links if d.lower() in ("in", "out", "up", "down")]
            if tags:
                tag = NonCardinalDirectionConnector(icon, tags)
                scene.addItem(tag)
                self._local_direction_tags.append(tag)

    def _draw_edges(self, scene: QGraphicsScene):
        """Draw both graphics and borders using the unified Connector class."""
        for a, b in self.global_graph.edges():
            key = frozenset((a, b))
            if key in self._local_drawn_edges:
                continue

            attrs = self.global_graph[a][b]
            door_state = attrs.get("door")  # "open", "closed", or None
            is_border = self.global_graph.is_border(a, b)

            icon_a = self._local_icons.get(a)
            icon_b = self._local_icons.get(b)

            # Both endpoints are visible
            if a in self._local_positions and b in self._local_positions:
                if not icon_a or not icon_b:
                    continue
                conn = CardinalDirectionConnector(icon_a, icon_b, door=door_state, border=is_border)
                conn.add_to_scene(scene)
                self.local_connectors[key] = conn
                self._local_drawn_edges.add(key)

            # One endpoint is outside the local graph (border arrows)
            elif is_border:
                anchor = a if a in self._local_positions else b
                other = b if anchor == a else a
                icon_anchor = self._local_icons.get(anchor)
                if not icon_anchor:
                    continue

                if other in self._local_positions:
                    icon_other = self._local_icons.get(other)
                    if not icon_other:
                        continue
                    kwargs = dict(icon_b=icon_other)
                else:
                    # If the other end is not visible, calculate the position for the arrow
                    dir_txt = next((d for d, dst in self.global_graph.get_room(anchor).links.items() if dst == other),
                                   "")
                    base, _ = split_suffix(dir_txt)
                    dx, dy = NUM_TO_DELTA.get(TEXT_TO_NUM.get(base, 8), (0, -1))
                    pos = icon_anchor.scenePos()
                    kwargs = dict(target_pos=QPointF(pos.x() + dx * GRID_SIZE, pos.y() + dy * GRID_SIZE))

                # Create a border connector with arrow visualization
                conn = CardinalDirectionConnector(icon_a=icon_anchor, door=door_state, border=True, **kwargs)
                conn.add_to_scene(scene)
                self.local_connectors[key] = conn
                self._local_drawn_edges.add(key)
