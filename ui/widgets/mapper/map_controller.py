# ui/widgets/mapper/map_controller.py

from PySide6.QtCore import QObject, Signal

from ui.widgets.mapper.location_widget import LocationWidget
from ui.widgets.mapper.room_icon      import RoomIcon
from ui.widgets.mapper.connector_item import ConnectorItem
from ui.widgets.mapper.map_graph      import MapGraph


class MapController(QObject):
    """
    Maintains a global topology graph and a spatially‐laid‐out local subgraph
    for rendering. Updates from GMCP.Room.Info packets drive both graphs;
    local_graph is rebuilt and redrawn on each update.
    """
    mapUpdated = Signal()

    # Direction name → numeric keypad code
    _TXT_TO_NUM = {
        "northwest": 7, "north": 8, "northeast": 9,
        "west": 4, "east": 6,
        "southwest": 1, "south": 2, "southeast": 3,
    }

    # Numeric keypad code → (dx, dy)
    _NUM_TO_DELTA = {
        1: (-1, +1), 2: ( 0, +1), 3: (+1, +1),
        4: (-1,  0),              6: (+1,  0),
        7: (-1, -1), 8: ( 0, -1), 9: (+1, -1),
    }

    def __init__(self, mapper_widget):
        super().__init__()
        self.map              = mapper_widget
        self.global_graph     = MapGraph()
        self.local_graph      = MapGraph()
        self._local_positions = {}     # room_hash -> (grid_x, grid_y)
        self._cur_hash        = None

        # track scene items for incremental redraw
        self._local_icons       = {}   # room_hash -> RoomIcon
        self._local_connectors  = {}   # frozenset((h1,h2)) -> ConnectorItem
        self._local_drawn_edges = set()

        self._marker = None
        self._prev_hash = None
        self._prev_links = {}  # links from the last room

    def on_room_info(self, info: dict):
        room_hash = info.get("hash")
        if not room_hash:
            return

        # 1) capture previous room and its links BEFORE changing self._cur_hash
        if self._cur_hash and self.global_graph.has_room(self._cur_hash):
            prev_room = self.global_graph.get_room(self._cur_hash)
            self._prev_links = dict(prev_room.links)
        else:
            self._prev_links = {}

        # 2) update/add room in global graph
        self.global_graph.add_or_update_room(info)

        # 3) set current room
        self._cur_hash = room_hash

        # now determine movement direction
        move_code = None
        move_dir = next(
            (d for d, dest in self._prev_links.items() if dest == room_hash),
            None
        )
        if move_dir:
            base_dir, _ = self._split_suffix(move_dir)
            move_code = self._TXT_TO_NUM.get(base_dir)

        # 4) build local graph + positions
        self.build_local_area()

        # 5) place or update marker
        gx, gy = self._local_positions.get(room_hash, (0, 0))
        if self._marker is None:
            self._marker = LocationWidget(gx, gy, direction_code=move_code)
            self.map.scene().addItem(self._marker)
        else:
            self._marker.update_position(gx, gy)
            self._marker.update_direction(move_code)

        # 6) render icons/connectors
        self._render_local_graph()
        self.mapUpdated.emit()

    def build_local_area(self) -> MapGraph:
        """
        Flood‐fill from self._cur_hash to compute integer (gx,gy) coords
        without overlap. Stores coords in self._local_positions and
        returns a fresh local_graph of those nodes + edges.
        """
        if not self._cur_hash or not self.global_graph.has_room(self._cur_hash):
            self.local_graph = MapGraph()
            self._local_positions.clear()
            return self.local_graph

        # 1) BFS + overlap‐aware layout
        positions = self.global_graph.layout_from_root(self._cur_hash)
        self._local_positions = positions

        # 2) assemble local subgraph
        local = MapGraph()
        for room_hash in positions:
            room = self.global_graph.get_room(room_hash)
            local.add_room(room)

        # 3) copy edges among these rooms
        for a, b in self.global_graph.edges():
            if a in positions and b in positions:
                local.connect_rooms(a, b)

        self.local_graph = local
        return local

    def _render_local_graph(self):
        """
        Clears previous RoomIcon/ConnectorItem items, then:
         - creates one RoomIcon per local_graph node at its (gx,gy)
         - draws one ConnectorItem per local_graph edge
        """
        scene = self.map.scene()

        # remove old icons
        for icon in self._local_icons.values():
            scene.removeItem(icon)
        self._local_icons.clear()

        # remove old connectors
        for conn in self._local_connectors.values():
            scene.removeItem(conn)
            if hasattr(conn, "symbol_item"):
                scene.removeItem(conn.symbol_item)
        self._local_connectors.clear()
        self._local_drawn_edges.clear()

        # draw fresh room icons
        for room_hash, data in self.local_graph.nodes(data=True):
            room = data["room"]
            gx, gy = self._local_positions[room_hash]

            icon = RoomIcon(
                grid_x=gx,
                grid_y=gy,
                short_desc=room.desc,
                terrain=room.terrain
            )
            room.icon = icon

            # RoomIcon.pos is precomputed in its ctor
            icon.setPos(icon.pos)
            scene.addItem(icon)
            self._local_icons[room_hash] = icon

        # draw fresh connectors
        for a, b in self.local_graph.edges():
            edge = frozenset((a, b))
            if edge in self._local_drawn_edges:
                continue

            r1 = self.local_graph.get_room(a).icon
            r2 = self.local_graph.get_room(b).icon
            conn = ConnectorItem(r1, r2)

            if hasattr(conn, "add_to_scene"):
                conn.add_to_scene(scene)
            else:
                scene.addItem(conn)

            self._local_connectors[edge] = conn
            self._local_drawn_edges.add(edge)

    def _split_suffix(self, dir_text: str) -> tuple[str, str | None]:
        """
        Strips trailing 'up' or 'down' from a direction like 'northeastup'.
        Returns (base_direction, suffix) where suffix ∈ {'up', 'down', None}
        """
        txt = dir_text.lower()
        if txt.endswith("up"):
            return txt[:-2], "up"
        if txt.endswith("down"):
            return txt[:-4], "down"
        return txt, None
