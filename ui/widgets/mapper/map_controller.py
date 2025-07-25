# ui/widgets/mapper/map_controller.py

import math
from PySide6.QtCore import QObject, Signal, QPointF
from PySide6.QtWidgets import QGraphicsScene

from ui.widgets.mapper.location_widget import LocationWidget
from ui.widgets.mapper.room_icon import RoomIcon
from ui.widgets.mapper.connector_item import (
    ConnectorItem, DoorConnectorItem, BorderConnectorItem,
    DoorBorderConnectorItem, NonCardinalDirectionTag
)
from ui.widgets.mapper.map_graph import MapGraph
from ui.widgets.mapper.constants import GRID_SIZE


class MapController(QObject):
    mapUpdated = Signal()

    _TXT_TO_NUM = {
        "northwest": 7, "north": 8, "northeast": 9,
        "west": 4, "east": 6,
        "southwest": 1, "south": 2, "southeast": 3,
    }

    _NUM_TO_DELTA = {
        1: (-1, +1), 2: (0, +1), 3: (+1, +1),
        4: (-1, 0), 6: (+1, 0),
        7: (-1, -1), 8: (0, -1), 9: (+1, -1),
    }

    def __init__(self, mapper_widget):
        super().__init__()
        self.map = mapper_widget
        self.global_graph = MapGraph()
        self.local_graph = MapGraph()
        self._local_positions = {}
        self._cur_hash = None

        self._local_icons = {}
        self._local_connectors = {}
        self._local_drawn_edges = set()
        self._local_border_arrows = []
        self._local_direction_tags = []
        self._marker = None
        self._prev_links = {}

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

        self._render_local_graph()
        self.mapUpdated.emit()

    def _calculate_move_code(self, prev_hash, current_hash):
        if not prev_hash:
            return None
        movedir = next((d for d, dest in self._prev_links.items() if dest == current_hash), None)
        if movedir:
            base, _ = self._split_suffix(movedir)
            return self._TXT_TO_NUM.get(base)
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

    def _render_local_graph(self):
        scene = self.map.scene()
        self._clear_scene_items(scene)
        self._draw_rooms(scene)
        self._draw_connectors(scene)
        self._draw_borders(scene)

    def _clear_scene_items(self, scene: QGraphicsScene):
        for item in (*self._local_border_arrows, *self._local_direction_tags):
            scene.removeItem(item)
        for icon in self._local_icons.values():
            scene.removeItem(icon)
        for conn in self._local_connectors.values():
            scene.removeItem(conn)
            if hasattr(conn, "symbol_item"):
                scene.removeItem(conn.symbol_item)

        self._local_border_arrows.clear()
        self._local_direction_tags.clear()
        self._local_icons.clear()
        self._local_connectors.clear()
        self._local_drawn_edges.clear()

    def _draw_rooms(self, scene: QGraphicsScene):
        for room_hash, data in self.local_graph.nodes(data=True):
            room = data["room"]
            gx, gy = self._local_positions[room_hash]
            icon = RoomIcon(grid_x=gx, grid_y=gy, short_desc=room.desc, terrain=room.terrain)
            room.icon = icon
            scene.addItem(icon)
            self._local_icons[room_hash] = icon

            tags = [d for d in map(str.lower, room.links) if d in ("in", "out", "up", "down")]
            if tags:
                tag = NonCardinalDirectionTag(icon, tags)
                scene.addItem(tag)
                self._local_direction_tags.append(tag)

    def _draw_connectors(self, scene: QGraphicsScene):
        for a, b in self.local_graph.edges():
            key = frozenset((a, b))
            if key in self._local_drawn_edges:
                continue

            attrs = self.global_graph[a][b]
            door_flag = attrs.get("door_open")
            icon_a = self.local_graph.get_room(a).icon
            icon_b = self.local_graph.get_room(b).icon

            conn = DoorConnectorItem(icon_a, icon_b, door_open=door_flag) if door_flag is not None else ConnectorItem(icon_a, icon_b)
            conn.add_to_scene(scene)

            self._local_connectors[key] = conn
            self._local_drawn_edges.add(key)

    def _draw_borders(self, scene: QGraphicsScene):
        for a, b in self.global_graph.edges():
            if not self.global_graph.is_border(a, b):
                continue
            if not (a in self._local_positions or b in self._local_positions):
                continue

            anchor = a if a in self._local_positions else b
            other = b if anchor == a else a
            icon_anchor = self.global_graph.get_room(anchor).icon
            door_flag = self.global_graph[a][b].get("door_open")

            if other in self._local_positions:
                icon_other = self.global_graph.get_room(other).icon
                kwargs = dict(icon_b=icon_other)
            else:
                dir_txt = next((d for d, dst in self.global_graph.get_room(anchor).links.items() if dst == other), "")
                base, _ = self._split_suffix(dir_txt)
                dx, dy = self._NUM_TO_DELTA.get(self._TXT_TO_NUM.get(base, 8), (0, -1))
                pos = icon_anchor.scenePos()
                kwargs = dict(target_pos=QPointF(pos.x() + dx * GRID_SIZE, pos.y() + dy * GRID_SIZE))

            connector_cls = DoorBorderConnectorItem if door_flag is not None else BorderConnectorItem
            arrow = connector_cls(icon_anchor, door_open=door_flag, **kwargs) if door_flag is not None else connector_cls(icon_anchor, **kwargs)
            arrow.a_hash, arrow.b_hash = anchor, other
            arrow.add_to_scene(scene)
            self._local_border_arrows.append(arrow)

    def _split_suffix(self, dir_text: str) -> tuple[str, str | None]:
        txt = dir_text.lower()
        if txt.endswith("up"):
            return txt[:-2], "up"
        if txt.endswith("down"):
            return txt[:-4], "down"
        return txt, None
