# ui/widgets/mapper/map_graph.py

import collections
import networkx as nx
from ui.widgets.mapper.room import Room

# Direction → (dx, dy) for *base* directions only
_TXT_TO_DELTA = {
    "northwest": (-1, -1), "north": ( 0, -1), "northeast": ( 1, -1),
    "west":      (-1,  0),                         "east": ( 1,  0),
    "southwest": (-1,  1), "south": ( 0,  1), "southeast": ( 1,  1),
}


def _strip_vertical_suffix(dir_text: str) -> str:
    txt = dir_text.lower()
    if txt.endswith("up"):
        return txt[:-2]
    if txt.endswith("down"):
        return txt[:-4]
    return txt


class MapGraph(nx.Graph):
    """
    A graph of Room instances.  Nodes are keyed by room.hash,
    stored in node attribute 'room'.  Edges carry optional flags:
      - 'border' (bool)   : blocks traversal
      - 'door_open' (bool): True=open door, False=closed door
    """

    def add_room(self, room: Room):
        """
        Insert a Room instance into the graph, if it doesn't already exist.
        """
        key = room.hash
        if not key:
            return
        if key not in self.nodes:
            self.add_node(key, room=room)
            room.graph_ref = self

    def add_or_update_room(self,
            info: dict,
            exit_types: dict[str, int] | None = None):
        """
        Create/update a Room from GMCP info, stub unseen neighbors,
        and connect edges, preserving existing 'border' and 'door_open'
        flags unless overridden by exit_types.

        exit_types maps direction names (e.g. 'north') to an integer:
          101  => open door
         -101  => closed door
        """
        exit_types = exit_types or {}
        room_hash = info.get("hash")
        if not room_hash:
            return

        # 1) Create or update the primary room node
        if room_hash in self.nodes:
            room = self.nodes[room_hash]["room"]
            room.desc    = info.get("short", room.desc)
            room.terrain = info.get("type", room.terrain)
            room.links   = info.get("links", room.links)
        else:
            room = Room(info)
            self.add_room(room)

        # 2) For each directional link, stub + (re)connect
        for dir_txt, dest_hash in room.links.items():
            if not dest_hash:
                continue

            # stub unseen room
            if dest_hash not in self.nodes:
                stub = Room({"hash": dest_hash})
                self.add_room(stub)

            # preserve existing flags if edge already exists
            existing_border    = False
            existing_door_open = None
            if self.has_edge(room_hash, dest_hash):
                data = self[room_hash][dest_hash]
                existing_border    = bool(data.get("border", False))
                existing_door_open = data.get("door_open", None)

            # determine new door_open from exit_types, else preserve
            code = exit_types.get(dir_txt)
            if code == 101:
                door_open = True
            elif code == -101:
                door_open = False
            else:
                door_open = existing_door_open

            # (re)connect with preserved or new flags
            self.connect_rooms(
                room_hash,
                dest_hash,
                border=existing_border,
                door_open=door_open
            )

    def has_room(self, room_hash: str) -> bool:
        return room_hash in self.nodes

    def get_room(self, room_hash: str) -> Room | None:
        data = self.nodes.get(room_hash)
        return data["room"] if data else None

    def connect_rooms(self,
            src_hash: str,
            dst_hash: str,
            border: bool = False,
            door_open: bool | None = None):
        """
        Add or update an edge if both nodes exist.
        'border=True' flags a non-traversable boundary.
        'door_open' sets a door flag (True=open, False=closed).
        """
        if src_hash in self.nodes and dst_hash in self.nodes:
            # prepare attributes
            attrs: dict[str, object] = {"border": bool(border)}
            if door_open is not None:
                attrs["door_open"] = bool(door_open)

            # add_edge will update existing attrs if edge exists
            self.add_edge(src_hash, dst_hash, **attrs)

    def set_border(self, a_hash: str, b_hash: str, border: bool = True):
        """
        Toggle the 'border' flag on an existing edge.
        """
        if self.has_edge(a_hash, b_hash):
            self[a_hash][b_hash]['border'] = bool(border)

    def is_border(self, a_hash: str, b_hash: str) -> bool:
        """
        Return True if the edge is marked as a boundary.
        """
        if self.has_edge(a_hash, b_hash):
            return bool(self[a_hash][b_hash].get('border', False))
        return False

    def layout_from_root(self, root_hash: str) -> dict[str, tuple[int, int]]:
        """
        Flood-fill from root_hash, mapping each room to a (grid_x, grid_y)
        coordinate by following links. Strips "up"/"down" suffix for placement.
        Stops traversing when a placement would overlap an existing room
        or when crossing an edge marked as 'border'.
        """
        if root_hash not in self.nodes:
            return {}

        positions: dict[str, tuple[int, int]] = {root_hash: (0, 0)}
        coord_owner: dict[tuple[int, int], str]    = {(0, 0): root_hash}
        queue = collections.deque([root_hash])

        while queue:
            cur = queue.popleft()
            cx, cy = positions[cur]
            room = self.get_room(cur)
            room.grid_x, room.grid_y = cx, cy

            for dir_txt, neigh in room.links.items():
                # block traversal across borders
                if self.is_border(cur, neigh):
                    continue

                if not neigh or neigh not in self.nodes:
                    continue

                base = _strip_vertical_suffix(dir_txt)
                delta = _TXT_TO_DELTA.get(base)
                if not delta:
                    continue
                dx, dy = delta

                # already placed?
                if neigh in positions:
                    continue

                # overlap check
                target = (cx + dx, cy + dy)
                owner  = coord_owner.get(target)
                if owner and owner != neigh:
                    continue

                positions[neigh] = target
                coord_owner[target] = neigh
                queue.append(neigh)

        return positions