# ui/widgets/mapper/map_controller.py

import math
from PySide6.QtCore import QObject, Signal, QPointF
from PySide6.QtWidgets import QGraphicsScene

from ui.widgets.mapper.location_widget       import LocationWidget
from ui.widgets.mapper.room_icon             import RoomIcon
from ui.widgets.mapper.connector_item import ConnectorItem, DoorConnectorItem, BorderConnectorItem, \
    NonCardinalDirectionTag
from ui.widgets.mapper.map_graph             import MapGraph
from ui.widgets.mapper.constants             import GRID_SIZE


class MapController(QObject):
    """
    Maintains global_graph and a laid-out local_graph.
    Edges can be:
      - normal (ConnectorItem)
      - doors (DoorConnectorItem, coded by exits:101/–101)
      - borders (BorderConnectorItem)
    """
    mapUpdated = Signal()

    _TXT_TO_NUM = {
        "northwest": 7, "north": 8, "northeast": 9,
        "west":      4,                  "east": 6,
        "southwest": 1, "south": 2, "southeast": 3,
    }
    _NUM_TO_DELTA = {
        1: (-1, +1), 2: (0, +1),  3: (+1, +1),
        4: (-1,  0),             6: (+1,  0),
        7: (-1, -1), 8: (0, -1),  9: (+1, -1),
    }

    def __init__(self, mapper_widget):
        super().__init__()
        self.map                = mapper_widget
        self.global_graph       = MapGraph()
        self.local_graph        = MapGraph()
        self._local_positions   = {}
        self._cur_hash          = None

        # scene item trackers
        self._local_icons         = {}
        self._local_connectors    = {}
        self._local_drawn_edges   = set()
        self._local_border_arrows = []
        self._local_direction_tags= []
        self._marker              = None
        self._prev_links          = {}

    def on_room_info(self, info: dict):
        """
        Called whenever GMCP.Room.Info arrives.
        Expects info["links"] and info["exits"].
        """
        room_hash = info.get("hash")
        if not room_hash:
            return

        # capture previous links for movement arrow
        if self._cur_hash and self.global_graph.has_room(self._cur_hash):
            self._prev_links = dict(self.global_graph.get_room(self._cur_hash).links)
        else:
            self._prev_links = {}

        # Pass the GMCP 'exits' dict into add_or_update_room
        exits = info.get("exits", {})    # e.g. {"north":101,"south":-101}
        self.global_graph.add_or_update_room(info, exit_types=exits)

        # set current room and compute move_code
        prev_hash = self._cur_hash
        self._cur_hash = room_hash
        move_code = None
        if prev_hash:
            movedir = next(
                (d for d, dest in self._prev_links.items() if dest == room_hash),
                None
            )
            if movedir:
                base, _ = self._split_suffix(movedir)
                move_code = self._TXT_TO_NUM.get(base)

        # rebuild the local submap (skips border edges)
        self.build_local_area()

        # update or place the player marker
        gx, gy = self._local_positions.get(room_hash, (0, 0))
        if self._marker is None:
            self._marker = LocationWidget(gx, gy, direction_code=move_code)
            self.map.scene().addItem(self._marker)
        else:
            self._marker.update_position(gx, gy)
            self._marker.update_direction(move_code)

        # redraw everything
        self._render_local_graph()
        self.mapUpdated.emit()

    def build_local_area(self) -> MapGraph:
        if not self._cur_hash or not self.global_graph.has_room(self._cur_hash):
            self.local_graph = MapGraph()
            self._local_positions.clear()
            return self.local_graph

        positions = self.global_graph.layout_from_root(self._cur_hash)
        self._local_positions = positions

        local = MapGraph()
        for h in positions:
            local.add_room(self.global_graph.get_room(h))

        for a, b in self.global_graph.edges():
            if a in positions and b in positions:
                if not self.global_graph.is_border(a, b):
                    local.connect_rooms(a, b)

        self.local_graph = local
        return local

    def _render_local_graph(self):
        """
        Clears previous items, then draws:
         - RoomIcon + NonCardinalDirectionTag for each room
         - ConnectorItem or DoorConnectorItem for each local edge
         - BorderConnectorItem for plain borders
         - DoorBorderConnectorItem for border-doors
        """
        scene = self.map.scene()

        # 1) clear old border‐arrows & direction‐tags
        for item in (*self._local_border_arrows, *self._local_direction_tags):
            scene.removeItem(item)
        self._local_border_arrows.clear()
        self._local_direction_tags.clear()

        # 2) clear old icons
        for icon in self._local_icons.values():
            scene.removeItem(icon)
        self._local_icons.clear()

        # 3) clear old connectors (and door symbols on them)
        for conn in self._local_connectors.values():
            scene.removeItem(conn)
            if hasattr(conn, "symbol_item"):
                scene.removeItem(conn.symbol_item)
        self._local_connectors.clear()
        self._local_drawn_edges.clear()

        # 4) draw RoomIcons + NonCardinalDirectionTag
        #from ui.widgets.mapper.non_cardinal_direction_tag import NonCardinalDirectionTag

        for room_hash, data in self.local_graph.nodes(data=True):
            room = data["room"]
            gx, gy = self._local_positions[room_hash]

            icon = RoomIcon(grid_x=gx, grid_y=gy,
                            short_desc=room.desc,
                            terrain=room.terrain)
            room.icon = icon
            scene.addItem(icon)
            self._local_icons[room_hash] = icon

            # attach in/out & up/down tags
            dirs = [d.lower() for d, dst in room.links.items() if dst]
            tags = [d for d in dirs if d in ("in", "out", "up", "down")]
            if tags:
                tag = NonCardinalDirectionTag(icon, tags)
                scene.addItem(tag)
                self._local_direction_tags.append(tag)

        # 5) draw normal connectors & doors
        for a, b in self.local_graph.edges():
            key = frozenset((a, b))
            if key in self._local_drawn_edges:
                continue

            attrs = self.global_graph[a][b]
            door_flag = attrs.get("door_open", None)

            icon_a = self.local_graph.get_room(a).icon
            icon_b = self.local_graph.get_room(b).icon

            if door_flag is not None:
                conn = DoorConnectorItem(icon_a, icon_b, door_open=door_flag)
            else:
                conn = ConnectorItem(icon_a, icon_b)

            conn.add_to_scene(scene)
            self._local_connectors[key] = conn
            self._local_drawn_edges.add(key)

            # 6) draw borders & border-doors
            from ui.widgets.mapper.connector_item import (
                BorderConnectorItem,
                DoorBorderConnectorItem
            )

            for a, b in self.global_graph.edges():
                if not self.global_graph.is_border(a, b):
                    continue

                in_a = a in self._local_positions
                in_b = b in self._local_positions
                if not (in_a or in_b):
                    continue

                anchor = a if in_a else b
                other = b if anchor == a else a
                icon_anchor = self.local_graph.get_room(anchor).icon
                door_flag = self.global_graph[a][b].get("door_open", None)

                # decide endpoint references
                if other in self._local_positions:
                    # both ends visible
                    icon_other = self.local_graph.get_room(other).icon
                    kwargs = dict(icon_b=icon_other)
                else:
                    # project one cell away
                    room = self.global_graph.get_room(anchor)
                    dir_txt = next((d for d, dst in room.links.items() if dst == other), "")
                    base, _ = self._split_suffix(dir_txt)
                    num = self._TXT_TO_NUM.get(base, 8)
                    dx, dy = self._NUM_TO_DELTA[num]
                    p = icon_anchor.scenePos()
                    target = QPointF(p.x() + dx * GRID_SIZE,
                                     p.y() + dy * GRID_SIZE)
                    kwargs = dict(target_pos=target)

                # pick the right connector class
                if door_flag is None:
                    arrow = BorderConnectorItem(icon_anchor, **kwargs)
                else:
                    arrow = DoorBorderConnectorItem(
                        icon_anchor,
                        door_open=door_flag,
                        **kwargs
                    )

                # tag for right‐click
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