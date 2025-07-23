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
    stored in node attribute 'room'.
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
        and connects them bidirectionally.
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

        # 2) Ensure stubs for every linked room
        for dest_hash in room.links.values():
            if not dest_hash:
                continue
            if dest_hash not in self.nodes:
                stub = Room({"hash": dest_hash})
                self.add_room(stub)

            # 3) Connect them
            self.add_edge(room_hash, dest_hash)

    def has_room(self, room_hash: str) -> bool:
        return room_hash in self.nodes

    def get_room(self, room_hash: str) -> Room | None:
        data = self.nodes.get(room_hash)
        return data["room"] if data else None

    def connect_rooms(self, src_hash: str, dst_hash: str):
        """
        Convenience: add an edge if both nodes exist.
        """
        if src_hash in self.nodes and dst_hash in self.nodes:
            self.add_edge(src_hash, dst_hash)

    def layout_from_root(self, root_hash: str) -> dict[str, tuple[int, int]]:
        """
        Flood-fill from root_hash, mapping each room to a (grid_x, grid_y)
        coordinate by following links.  Strips "up"/"down" suffix for placement.
        Stops traversing when a placement would overlap an existing room.
        """
        if root_hash not in self.nodes:
            return {}

        positions: dict[str, tuple[int, int]] = {root_hash: (0, 0)}
        coord_owner: dict[tuple[int,int], str] = {(0, 0): root_hash}
        queue = collections.deque([root_hash])

        while queue:
            cur = queue.popleft()
            cx, cy = positions[cur]
            room = self.get_room(cur)
            room.grid_x, room.grid_y = cx, cy

            for dir_txt, neigh in room.links.items():
                if not neigh or neigh not in self.nodes:
                    continue

                base = _strip_vertical_suffix(dir_txt)
                delta = _TXT_TO_DELTA.get(base)
                if not delta:
                    continue
                dx, dy = delta

                # Already positioned?
                if neigh in positions:
                    # if placement mismatches, skip
                    if positions[neigh] != (cx + dx, cy + dy):
                        continue
                    else:
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