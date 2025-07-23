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
    A graph of Room instances. Nodes are keyed by room.hash,
    stored in node attribute 'room'. Edges carry an optional
    'border' flag (bool) to mark non-traversable boundaries.
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

    def add_or_update_room(self, info: dict):
        """
        Creates or updates a Room node from GMCP info, then
        stubs out placeholders for any linked-but-unseen rooms
        and (re)connects them, preserving any existing border flag.
        """
        room_hash = info.get("hash")
        if not room_hash:
            return

        # 1) Create or update the primary room
        if room_hash in self.nodes:
            room = self.nodes[room_hash]["room"]
            room.desc    = info.get("short", room.desc)
            room.terrain = info.get("type", room.terrain)
            room.links   = info.get("links", room.links)
        else:
            room = Room(info)
            self.add_room(room)

        # 2) Ensure stubs + (re)connect, preserving border
        for dest_hash in room.links.values():
            if not dest_hash:
                continue

            # create stub if needed
            if dest_hash not in self.nodes:
                stub = Room({"hash": dest_hash})
                self.add_room(stub)

            # preserve any existing border flag
            existing_border = False
            if self.has_edge(room_hash, dest_hash):
                existing_border = bool(
                    self[room_hash][dest_hash].get("border", False)
                )

            # (re)connect with preserved flag
            self.connect_rooms(room_hash, dest_hash, border=existing_border)

    def has_room(self, room_hash: str) -> bool:
        return room_hash in self.nodes

    def get_room(self, room_hash: str) -> Room | None:
        data = self.nodes.get(room_hash)
        return data["room"] if data else None

    def connect_rooms(self, src_hash: str, dst_hash: str, border: bool = False):
        """
        Convenience: add or update an edge if both nodes exist.
        'border=True' flags this connection as a non-traversable boundary.
        """
        if src_hash in self.nodes and dst_hash in self.nodes:
            self.add_edge(src_hash, dst_hash, border=bool(border))

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
        Stops traversing when a placement would overlap an existing room,
        or when crossing a border edge.
        """
        if root_hash not in self.nodes:
            return {}

        positions: dict[str, tuple[int, int]] = {root_hash: (0, 0)}
        coord_owner: dict[tuple[int, int], str] = {(0, 0): root_hash}
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

                # Already positioned?
                if neigh in positions:
                    continue

                # Overlap check
                target = (cx + dx, cy + dy)
                owner = coord_owner.get(target)
                if owner and owner != neigh:
                    continue

                positions[neigh] = target
                coord_owner[target] = neigh
                queue.append(neigh)

        return positions