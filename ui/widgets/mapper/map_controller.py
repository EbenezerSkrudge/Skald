# ui/widgets/mapper/map_controller.py

import math
from PySide6.QtCore   import QObject, Signal
from PySide6.QtGui    import QColor

from ui.widgets.mapper.room_item        import RoomItem
from ui.widgets.mapper.connector_item   import ConnectorItem, NonCardinalDirectionTag
from ui.widgets.mapper.location_widget  import LocationWidget
from ui.widgets.mapper.constants        import GRID_SIZE
from game.terrain                       import TERRAIN_TYPES


class MapController(QObject):
    """
    Call `on_room_info(info: dict)` for each GMCP.Room.Info dict.
    Auto‐places explored and unexplored rooms, draws connectors,
    moves the LocationWidget, and keeps the view centered.
    """
    mapUpdated = Signal()

    _TXT_TO_NUM = {
        "northwest": 7, "north": 8, "northeast": 9,
        "west":       4,             "east": 6,
        "southwest": 1, "south":  2, "southeast": 3,
    }

    _NUM_TO_DELTA = {
         1: (-1, +1), 2: ( 0, +1), 3: (+1, +1),
         4: (-1,  0),             6: (+1,  0),
         7: (-1, -1), 8: ( 0, -1), 9: (+1, -1),
    }

    def __init__(self, mapper_widget):
        super().__init__()
        self.map            = mapper_widget
        self._rooms         = {}    # room_hash -> (gx, gy, RoomItem)
        self._occupied      = set() # set of (gx, gy)
        self._drawn_edges   = set() # frozenset({hash1, hash2})
        self._cur_hash      = None
        self._prev_info     = None
        self._marker        = None
        self._last_vertical = None

    def on_room_info(self, info: dict):
        # normalize hash
        room_hash = info.get("hash")
        if room_hash == "0" or not room_hash:
            if self._marker:
                self._marker.update_direction(None)
            self._prev_info = info
            return

        links      = info.get("links", {}) or {}
        terrain    = info.get("type")
        short_desc = info.get("short", "???")
        color_hex  = TERRAIN_TYPES.get(terrain, ("unknown", "#888"))[1]
        explored_color = QColor(color_hex)

        # 1) first room
        if self._cur_hash is None:
            gx, gy = 0, 0
            self._place_room(room_hash, gx, gy,
                             short_desc, explored_color, explored=True)
            # spawn marker (arrow hidden)
            self._marker = LocationWidget(gx, gy, None)
            self.map.scene().addItem(self._marker)
            # ghost‐place & connect exits
            self._preplace_and_connect(
                links,
                origin_hash=room_hash,
                gx=gx, gy=gy
            )
            self._cur_hash, self._prev_info = room_hash, info
            self.mapUpdated.emit()
            return

        # 2) find which exit we took
        prev_links = self._prev_info.get("links", {}) or {}
        move_txt   = next(
            (d for d, dest in prev_links.items() if dest == room_hash),
            None
        )
        if not move_txt:
            self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return

        base_dir, vertical = self._split_suffix(move_txt)
        self._last_vertical = vertical

        num_code = self._TXT_TO_NUM.get(base_dir)
        delta    = self._NUM_TO_DELTA.get(num_code) if num_code else None
        if num_code is None or delta is None:
            self._marker.update_direction(None)
            self._cur_hash, self._prev_info = room_hash, info
            return

        dx, dy       = delta
        ox, oy, old_item = self._rooms[self._cur_hash]
        nx, ny       = ox + dx, oy + dy

        # 3) explore placeholder or place new
        if room_hash in self._rooms:
            _, _, placeholder = self._rooms[room_hash]
            if not placeholder.explored:
                placeholder.color      = explored_color
                placeholder.label_text = short_desc
                placeholder.set_explored(True)
                placeholder.setToolTip(short_desc)    # update tooltip
        else:
            self._place_room(room_hash, nx, ny,
                             short_desc, explored_color, explored=True)

        # 4) connect old -> new
        self._draw_connector(self._cur_hash, room_hash)

        # 5) move & orient marker
        self._marker.update_position(nx, ny)
        self._marker.update_direction(num_code)
        # recenter view
        self.map.ensure_padding()
        self.map.center_on_grid(nx, ny)

        # 6) ghost‐place & connect new neighbors
        self._preplace_and_connect(
            links,
            origin_hash=room_hash,
            gx=nx, gy=ny
        )

        self._cur_hash, self._prev_info = room_hash, info
        self.mapUpdated.emit()

    def _split_suffix(self, dir_text: str) -> tuple[str,str|None]:
        txt = dir_text.lower()
        if txt.endswith("up"):
            return txt[:-2], "up"
        if txt.endswith("down"):
            return txt[:-4], "down"
        return txt, None

    def _place_room(
        self,
        room_hash: str,
        gx: int,
        gy: int,
        short_desc: str,
        color: QColor,
        explored: bool
    ):
        # fold overlaps
        if (gx, gy) in self._occupied:
            origin = self._rooms[self._cur_hash][2]
            self.map.scene().addItem(NonCardinalDirectionTag(origin, []))
            return

        self._occupied.add((gx, gy))
        room = RoomItem(gx, gy, short_desc, color, explored)
        self._rooms[room_hash] = (gx, gy, room)
        self.map.scene().addItem(room)

    def _draw_connector(self, hash1: str, hash2: str):
        edge = frozenset({hash1, hash2})
        if edge in self._drawn_edges:
            return
        self._drawn_edges.add(edge)

        room1 = self._rooms[hash1][2]
        room2 = self._rooms[hash2][2]
        conn  = ConnectorItem(room1, room2)
        if hasattr(conn, "add_to_scene"):
            conn.add_to_scene(self.map.scene())
        else:
            self.map.scene().addItem(conn)

    def _preplace_and_connect(
        self,
        links: dict,
        origin_hash: str,
        gx: int,
        gy: int
    ):
        for dir_text, dest_hash in links.items():
            if not dest_hash:
                continue

            base_dir = self._split_suffix(dir_text)[0]
            num_code = self._TXT_TO_NUM.get(base_dir)
            delta    = self._NUM_TO_DELTA.get(num_code) if num_code else None
            if num_code is None or delta is None:
                continue

            dx, dy = delta
            ex, ey = gx + dx, gy + dy

            # unexplored placeholder
            if dest_hash not in self._rooms:
                self._place_room(dest_hash, ex, ey,
                                 "unexplored", QColor("#888"), explored=False)

            # always draw connector
            self._draw_connector(origin_hash, dest_hash)