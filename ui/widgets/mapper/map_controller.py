# ui/widgets/mapper/map_controller.py

from PySide6.QtCore import QObject, Signal
from ui.widgets.mapper.connector_item import ConnectorItem
from ui.widgets.mapper.location_widget import LocationWidget
from ui.widgets.mapper.map_graph import MapGraph
from ui.widgets.mapper.room import Room


class MapController(QObject):
    """
    Call on_room_info(info: dict) for each GMCP.Room.Info dict.
    Places and connects rooms, manages marker movement, and keeps the view centered.
    """
    mapUpdated = Signal()

    # Direction name → numeric keypad code
    _TXT_TO_NUM = {
        "northwest": 7, "north": 8, "northeast": 9,
        "west": 4,                  "east": 6,
        "southwest": 1, "south": 2, "southeast": 3,
    }

    # Numeric keypad code → (dx, dy)
    _NUM_TO_DELTA = {
        1: (-1, +1), 2: (0, +1),  3: (+1, +1),
        4: (-1,  0),             6: (+1,  0),
        7: (-1, -1), 8: (0, -1),  9: (+1, -1),
    }

    def __init__(self, mapper_widget):
        super().__init__()
        self.map = mapper_widget

        self.graph = MapGraph()
        self._connectors = {}      # frozenset((h1,h2)) -> ConnectorItem
        self._drawn_edges = set()  # set of frozenset((h1,h2))
        self._marker = None        # LocationWidget
        self._cur_hash = None      # current room hash
        self._prev_info = None     # last GMCP.Room.Info dict

    def on_room_info(self, info: dict):
        room_hash = info.get("hash")
        if not room_hash or room_hash == "0":
            # no valid room—just reset marker direction
            if self._marker:
                self._marker.update_direction(None)
            self._prev_info = info
            return

        links   = info.get("links", {})
        desc    = info.get("short", "no description")
        terrain = info.get("type", "unknown")

        # 1) First room ever: place root at (0,0)
        if self._cur_hash is None:
            root = Room(info, 0, 0)
            self.graph.add_room(root)
            self.map.scene().addItem(root.render())

            self._marker = LocationWidget(0, 0, None)
            self.map.scene().addItem(self._marker)

            self._preplace_and_connect(root)
            self._cur_hash, self._prev_info = root.hash, info

            self._update_layout_and_marker()
            self.mapUpdated.emit()
            return

        # 2) Movement? find direction from previous room
        prev_links = self._prev_info.get("links", {})
        move_dir   = next(
            (d for d, dest in prev_links.items() if dest == room_hash),
            None
        )
        if not move_dir:
            if self._marker:
                self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return

        base_dir, vert = self._split_suffix(move_dir)
        num_code = self._TXT_TO_NUM.get(base_dir)
        delta    = self._NUM_TO_DELTA.get(num_code)
        if not delta:
            self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return
        dx, dy = delta

        # 3) Discover or update the destination room
        if not self.graph.has_room(room_hash):
            candidate = Room(info, 0, 0)
            self.graph.add_room(candidate)
            self.map.scene().addItem(candidate.render())
        else:
            candidate = self.graph.get_room(room_hash)
            candidate.update_from_gmcp(info)

        # 4) Connect in graph (connector drawn later)
        self.graph.connect_rooms(self._cur_hash, room_hash)

        # 5) Preplace neighbors (unexplored only)
        current_room = self.graph.get_room(room_hash)
        self._preplace_and_connect(current_room)

        # 6) Update state, layout, marker
        self._cur_hash, self._prev_info = room_hash, info
        self._update_layout_and_marker(num_code)
        self.mapUpdated.emit()

    def _preplace_and_connect(self, room: Room):
        """
        For each exit in room.links, preplace an 'unexplored' Room
        and connect it in the graph.
        """
        for dir_txt, dest_hash in room.links.items():
            if not dest_hash:
                continue

            base_dir, _ = self._split_suffix(dir_txt)
            num_code = self._TXT_TO_NUM.get(base_dir)
            if not self._NUM_TO_DELTA.get(num_code):
                continue

            if not self.graph.has_room(dest_hash):
                info_unexp = {
                    "hash":  dest_hash,
                    "short": "?",
                    "type":  "unexplored",
                    "area":  room.area,
                    "links": {}
                }
                shunt = Room(info_unexp, 0, 0)
                self.graph.add_room(shunt)
                self.map.scene().addItem(shunt.render())

            self.graph.connect_rooms(room.hash, dest_hash)
            # connector drawing deferred to layout step

    def _update_layout_and_marker(self, num_code: int | None = None):
        """
        Run overlap‐safe layout, reposition all rooms & marker,
        then draw/refresh all connectors, recenter view.
        """
        # 1) layout
        positions = self.graph.layout_from_root(self._cur_hash)
        for room_hash, (gx, gy) in positions.items():
            room = self.graph.get_room(room_hash)
            room.grid_x, room.grid_y = gx, gy
            room.icon.setPos(room.position)

        # 2) marker
        current = self.graph.get_room(self._cur_hash)
        self._marker.update_position(current.grid_x, current.grid_y)
        if num_code is not None:
            self._marker.update_direction(num_code)

        # 3) draw any new connectors now that rooms are placed
        for h1, h2 in self.graph.edges():
            edge = frozenset((h1, h2))
            if edge in self._drawn_edges:
                continue
            self._drawn_edges.add(edge)

            conn = ConnectorItem(
                self.graph.get_room(h1),
                self.graph.get_room(h2)
            )
            if hasattr(conn, "add_to_scene"):
                conn.add_to_scene(self.map.scene())
            else:
                self.map.scene().addItem(conn)
            self._connectors[edge] = conn

        # 4) refresh all connectors so they follow moved rooms
        for conn in self._connectors.values():
            conn.refresh()

        # 5) pad & center
        self.map.ensure_padding()
        self.map.center_on_grid(current.grid_x, current.grid_y)

    def _split_suffix(self, dir_text: str) -> tuple[str, str | None]:
        txt = dir_text.lower()
        if txt.endswith("up"):
            return txt[:-2], "up"
        if txt.endswith("down"):
            return txt[:-4], "down"
        return txt, None
