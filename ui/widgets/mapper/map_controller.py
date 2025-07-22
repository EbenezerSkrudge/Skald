# ui/widgets/mapper/map_controller.py

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
        self._rooms = {}        # room_hash -> (gx, gy, RoomItem)
        self._connectors = {}   # frozenset((h1, h2)) -> ConnectorItem
        self._occupied = set()  # set of (gx, gy)
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

        links   = info.get("links", {})
        desc    = info.get("short", "no description")
        terrain = info.get("type")
        area    = info.get("area", "unknown")  # Supplied via GMCP or spoofed upstream

        # First room ever
        if self._cur_hash is None:
            self._place_room(room_hash, 0, 0, desc, terrain, area=area, explored=True)
            self._marker = LocationWidget(0, 0, None)
            self.map.scene().addItem(self._marker)
            self._preplace_and_connect(links, room_hash, 0, 0)
            self._cur_hash, self._prev_info = room_hash, info
            self.mapUpdated.emit()
            return

        # Determine if this is a movement into a linked room
        prev_links = self._prev_info.get("links", {})
        move_txt   = next((d for d, dest in prev_links.items() if dest == room_hash), None)

        if not move_txt:
            self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return

        base_dir, vertical = self._split_suffix(move_txt)
        num_code = self._TXT_TO_NUM.get(base_dir)
        delta    = self._NUM_TO_DELTA.get(num_code)

        if not delta:
            self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return

        self._last_vertical = vertical
        dx, dy = delta
        ox, oy, _ = self._rooms[self._cur_hash]
        nx, ny = ox + dx, oy + dy

        # If room preplaced as unexplored, now we explore it
        if room_hash in self._rooms:
            _, _, room = self._rooms[room_hash]
            if not room.explored:
                color = QColor(TERRAIN_TYPES.get(terrain, ("unknown", "#888"))[1])
                room.color = color
                room.label_text = desc
                room.set_explored(True)
                room.setToolTip(desc)
                # Update graph area from fresh GMCP info
                self.graph.nodes[room_hash]["area"] = area
                # Refresh label/filter if it's the current room
                if room_hash == self._cur_hash:
                    self.mapUpdated.emit()
        else:
            # Brand-new room discovered via movement
            self._place_room(room_hash, nx, ny, desc, terrain, area=area, explored=True)

        # Connect, move marker, re-center
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
        if txt.endswith("up"):
            return txt[:-2], "up"
        if txt.endswith("down"):
            return txt[:-4], "down"
        return txt, None

    def _place_room(self, room_hash: str, gx: int, gy: int,
                    desc: str, terrain: str, area: str, explored: bool):
        if (gx, gy) in self._occupied:
            origin = self._rooms[self._cur_hash][2]
            self.map.scene().addItem(NonCardinalDirectionTag(origin, []))
            return

        color_hex = TERRAIN_TYPES.get(terrain, ("unknown", "#888"))[1]
        color     = QColor(color_hex)

        room = RoomItem(gx, gy, desc, color, explored)
        self._occupied.add((gx, gy))
        self._rooms[room_hash] = (gx, gy, room)
        self.map.scene().addItem(room)

        self.graph.add_node(
            room_hash,
            pos=(gx, gy),
            desc=desc,
            explored=explored,
            terrain=terrain,
            area=area,
        )

    def _draw_connector(self, hash1: str, hash2: str):
        if hash1 not in self._rooms or hash2 not in self._rooms:
            return  # Prevents KeyError if either room isn't placed yet

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
        self._connectors[edge] = conn

    def _preplace_and_connect(self, links: dict, origin_hash: str, gx: int, gy: int):
        for dir_text, dest_hash in links.items():
            if not dest_hash:
                continue

            base_dir = self._split_suffix(dir_text)[0]
            num_code = self._TXT_TO_NUM.get(base_dir)
            delta    = self._NUM_TO_DELTA.get(num_code)
            if not delta:
                continue

            dx, dy = delta
            nx, ny = gx + dx, gy + dy

            if dest_hash not in self._rooms:
                # Preplace unexplored with no area until explored
                self._place_room(dest_hash, nx, ny, "unexplored", None, area="unknown", explored=False)

            self._draw_connector(origin_hash, dest_hash)

    def find_room_hash(self, room_item):
        for h, (_, _, item) in self._rooms.items():
            if item is room_item:
                return h
        return None

    def set_room_area(self, room_hash, new_area):
        if room_hash in self.graph.nodes:
            self.graph.nodes[room_hash]["area"] = new_area
            self.mapUpdated.emit()

    def delete_room(self, room_hash):
        if room_hash not in self._rooms:
            return

        gx, gy, item = self._rooms.pop(room_hash)
        self._occupied.discard((gx, gy))
        self.map.scene().removeItem(item)
        self.graph.remove_node(room_hash)

        edges_to_remove = [e for e in self._drawn_edges if room_hash in e]
        for edge in edges_to_remove:
            self._drawn_edges.remove(edge)
            conn = self._connectors.pop(edge, None)
            if conn:
                self.map.scene().removeItem(conn)