# ui/widgets/mapper/map_controller.py

from PySide6.QtCore import QObject, Signal, QPointF

from ui.widgets.mapper.location_widget       import LocationWidget
from ui.widgets.mapper.room_icon             import RoomIcon
from ui.widgets.mapper.connector_item        import ConnectorItem, BorderConnectorItem
from ui.widgets.mapper.map_graph             import MapGraph
from ui.widgets.mapper.constants             import GRID_SIZE


class MapController(QObject):
    """
    Maintains a global topology graph and a spatially-laid-out local subgraph
    for rendering. Honors 'border' flags to block traversal and draw arrows.
    """
    mapUpdated = Signal()

    # Direction name → numeric keypad code
    _TXT_TO_NUM = {
        "northwest": 7, "north": 8, "northeast": 9,
        "west":      4,                  "east": 6,
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
        self.map               = mapper_widget
        self.global_graph      = MapGraph()
        self.local_graph       = MapGraph()
        self._local_positions  = {}    # room_hash -> (grid_x, grid_y)
        self._cur_hash         = None

        # Scene items tracking
        self._local_icons        = {}   # room_hash -> RoomIcon
        self._local_connectors   = {}   # frozenset((h1,h2)) -> ConnectorItem
        self._local_drawn_edges  = set()
        self._local_border_arrows = []  # list of BorderConnectorItem

        # Player position marker
        self._marker     = None
        self._prev_links = {}

    def on_room_info(self, info: dict):
        room_hash = info.get("hash")
        if not room_hash:
            return

        # Capture previous room's links
        if self._cur_hash and self.global_graph.has_room(self._cur_hash):
            prev_room = self.global_graph.get_room(self._cur_hash)
            self._prev_links = dict(prev_room.links)
        else:
            self._prev_links = {}

        # Update global graph
        self.global_graph.add_or_update_room(info)

        # Determine movement direction
        prev_hash = self._cur_hash
        self._cur_hash = room_hash

        move_code = None
        if prev_hash:
            move_dir = next(
                (d for d, dest in self._prev_links.items() if dest == room_hash),
                None
            )
            if move_dir:
                base, _ = self._split_suffix(move_dir)
                move_code = self._TXT_TO_NUM.get(base)

        # Rebuild local subgraph (respects borders)
        self.build_local_area()

        # Place or update the player marker
        gx, gy = self._local_positions.get(room_hash, (0, 0))
        if self._marker is None:
            self._marker = LocationWidget(gx, gy, direction_code=move_code)
            self.map.scene().addItem(self._marker)
        else:
            self._marker.update_position(gx, gy)
            self._marker.update_direction(move_code)

        # Redraw icons, connectors, borders
        self._render_local_graph()
        self.mapUpdated.emit()

    def build_local_area(self) -> MapGraph:
        """
        Flood-fill from self._cur_hash to assign (grid_x, grid_y) coords,
        then build a local_graph including only non-border edges.
        """
        if not self._cur_hash or not self.global_graph.has_room(self._cur_hash):
            self.local_graph = MapGraph()
            self._local_positions.clear()
            return self.local_graph

        # 1) Compute positions via global_graph
        positions = self.global_graph.layout_from_root(self._cur_hash)
        self._local_positions = positions

        # 2) Assemble node set in a fresh MapGraph
        local = MapGraph()
        for room_hash in positions:
            room = self.global_graph.get_room(room_hash)
            local.add_room(room)

        # 3) Copy only non-border edges
        for a, b in self.global_graph.edges():
            if a in positions and b in positions:
                if not self.global_graph.is_border(a, b):
                    local.connect_rooms(a, b)

        self.local_graph = local
        return local

    def _render_local_graph(self):
        """
        Clears old items, then draws:
          - RoomIcon for each local node
          - ConnectorItem for each local edge
          - BorderConnectorItem for each border edge touching the local map
        """
        scene = self.map.scene()

        # Clear old border arrows
        for arr in self._local_border_arrows:
            scene.removeItem(arr)
        self._local_border_arrows.clear()

        # Remove old room icons
        for icon in self._local_icons.values():
            scene.removeItem(icon)
        self._local_icons.clear()

        # Remove old connectors
        for conn in self._local_connectors.values():
            scene.removeItem(conn)
            if hasattr(conn, "symbol_item"):
                scene.removeItem(conn.symbol_item)
        self._local_connectors.clear()
        self._local_drawn_edges.clear()

        # Draw fresh RoomIcons
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
            scene.addItem(icon)
            self._local_icons[room_hash] = icon

        # Draw fresh ConnectorItems
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

        # Draw border arrows for edges marked border
        for a, b in self.global_graph.edges():
            if not self.global_graph.is_border(a, b):
                continue

            in_a = a in self._local_positions
            in_b = b in self._local_positions

            # Skip if neither side is visible
            if not (in_a or in_b):
                continue

            # Anchor on the in-map room
            anchor_hash = a if in_a else b
            other_hash  = b if anchor_hash == a else a

            icon_anchor = self.local_graph.get_room(anchor_hash).icon

            if other_hash in self._local_positions:
                # Neighbor is in the map: draw between two icons
                icon_other = self.local_graph.get_room(other_hash).icon
                arrow = BorderConnectorItem(icon_anchor,
                                            icon_b=icon_other)
            else:
                # Neighbor is out-of-bounds: project one GRID_SIZE cell away
                room    = self.global_graph.get_room(anchor_hash)
                dir_txt = next(
                    (d for d, dest in room.links.items()
                     if dest == other_hash),
                    ""
                )
                base, _ = self._split_suffix(dir_txt)
                num     = self._TXT_TO_NUM.get(base, 8)  # default north
                dx, dy  = self._NUM_TO_DELTA[num]

                p        = icon_anchor.scenePos()
                target_p = QPointF(p.x() + dx * GRID_SIZE,
                                   p.y() + dy * GRID_SIZE)

                arrow = BorderConnectorItem(icon_anchor,
                                            target_pos=target_p)

            arrow.add_to_scene(scene)
            self._local_border_arrows.append(arrow)

    def _split_suffix(self, dir_text: str) -> tuple[str, str | None]:
        """
        Strips trailing 'up' or 'down' from a direction like 'northeastup'.
        Returns (base_direction, suffix) where suffix ∈ {'up','down',None}
        """
        txt = dir_text.lower()
        if txt.endswith("up"):
            return txt[:-2], "up"
        if txt.endswith("down"):
            return txt[:-4], "down"
        return txt, None