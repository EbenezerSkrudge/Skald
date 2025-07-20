# ui/widgets/mapper/map_controller.py

import math

import networkx as nx

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from ui.widgets.mapper.room_item import RoomItem
from ui.widgets.mapper.connector_item import ConnectorItem, NonCardinalDirectionTag
from ui.widgets.mapper.location_widget import LocationWidget
from ui.widgets.mapper.constants import GRID_SIZE
from game.terrain import TERRAIN_TYPES


class MapController(QObject):
    """
    Call `on_room_info(info: dict)` for each GMCP.Room.Info dict.
    Places and connects rooms, manages marker movement, and keeps the view centered.
    """
    mapUpdated = Signal()

    _TXT_TO_NUM = {
        "northwest": 7, "north": 8, "northeast": 9,
        "west": 4,                  "east": 6,
        "southwest": 1, "south": 2, "southeast": 3,
    }

    _NUM_TO_DELTA = {
         1: (-1, +1), 2: (0, +1), 3: (+1, +1),
         4: (-1,  0),             6: (+1,  0),
         7: (-1, -1), 8: (0, -1), 9: (+1, -1),
    }

    def __init__(self, mapper_widget):
        super().__init__()
        self.map = mapper_widget
        self._rooms = {}       # room_hash -> (gx, gy, RoomItem)
        self._occupied = set() # set of (gx, gy)
        self._drawn_edges = set()
        self._cur_hash = None
        self._prev_info = None
        self._marker = None
        self._last_vertical = None

        self.graph = nx.Graph()

    def on_room_info(self, info: dict):
        room_hash = info.get("hash")
        if not room_hash or room_hash == "0":
            if self._marker:
                self._marker.update_direction(None)
            self._prev_info = info
            return

        links = info.get("links", {})
        desc = info.get("short", "???")
        terrain = info.get("type")
        color = QColor(TERRAIN_TYPES.get(terrain, ("unknown", "#888"))[1])

        # First room placement
        if self._cur_hash is None:
            self._place_room(room_hash, 0, 0, desc, color, explored=True)
            self._marker = LocationWidget(0, 0, None)
            self.map.scene().addItem(self._marker)
            self._preplace_and_connect(links, room_hash, 0, 0)
            self._cur_hash, self._prev_info = room_hash, info
            self.mapUpdated.emit()
            return

        # Determine direction taken from previous room
        prev_links = self._prev_info.get("links", {})
        move_txt = next((d for d, dest in prev_links.items() if dest == room_hash), None)

        if not move_txt:
            self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return

        base_dir, vertical = self._split_suffix(move_txt)
        num_code = self._TXT_TO_NUM.get(base_dir)
        delta = self._NUM_TO_DELTA.get(num_code)

        if not delta:
            self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return

        self._last_vertical = vertical

        dx, dy = delta
        ox, oy, old_room = self._rooms[self._cur_hash]
        nx, ny = ox + dx, oy + dy

        # Update placeholder or place new
        if room_hash in self._rooms:
            _, _, room = self._rooms[room_hash]
            if not room.explored:
                room.color = color
                room.label_text = desc
                room.set_explored(True)
                room.setToolTip(desc)
        else:
            self._place_room(room_hash, nx, ny, desc, color, explored=True)

        # Draw connector and move marker
        self._draw_connector(self._cur_hash, room_hash)
        self._marker.update_position(nx, ny)
        self._marker.update_direction(num_code)

        self.map.ensure_padding()
        self.map.center_on_grid(nx, ny)
        self._preplace_and_connect(links, room_hash, nx, ny)

        self._cur_hash, self._prev_info = room_hash, info
        self.mapUpdated.emit()

    def _split_suffix(self, dir_text: str) -> tuple[str, str | None]:
        txt = dir_text.lower()
        if txt.endswith("up"): return txt[:-2], "up"
        if txt.endswith("down"): return txt[:-4], "down"
        return txt, None

    def _place_room(self, room_hash: str, gx: int, gy: int,
                    desc: str, color: QColor, explored: bool):
        if (gx, gy) in self._occupied:
            origin = self._rooms[self._cur_hash][2]
            self.map.scene().addItem(NonCardinalDirectionTag(origin, []))
            return

        room = RoomItem(gx, gy, desc, color, explored)
        self._occupied.add((gx, gy))
        self._rooms[room_hash] = (gx, gy, room)
        self.map.scene().addItem(room)

        self.graph.add_node(room_hash, pos=(gx, gy), desc=desc, explored=explored)

    def _draw_connector(self, hash1: str, hash2: str):
        edge = frozenset((hash1, hash2))
        if edge in self._drawn_edges:
            return
        self._drawn_edges.add(edge)

        room1, room2 = self._rooms[hash1][2], self._rooms[hash2][2]
        conn = ConnectorItem(room1, room2)

        if hasattr(conn, "add_to_scene"):
            conn.add_to_scene(self.map.scene())
        else:
            self.map.scene().addItem(conn)

        self.graph.add_edge(hash1, hash2)

    def _preplace_and_connect(self, links: dict, origin_hash: str, gx: int, gy: int):
        for dir_text, dest_hash in links.items():
            if not dest_hash:
                continue

            base_dir = self._split_suffix(dir_text)[0]
            num_code = self._TXT_TO_NUM.get(base_dir)
            delta = self._NUM_TO_DELTA.get(num_code)

            if not delta:
                continue

            dx, dy = delta
            nx, ny = gx + dx, gy + dy

            if dest_hash not in self._rooms:
                self._place_room(dest_hash, nx, ny, "unexplored", QColor("#888"), explored=False)

            self._draw_connector(origin_hash, dest_hash)
