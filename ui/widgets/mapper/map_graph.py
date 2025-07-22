# ui/widgets/mapper/map_graph.py

import collections
import networkx as nx
from ui.widgets.mapper.room import Room

# Direction → (dx, dy) for *base* directions only
_TXT_TO_DELTA = {
    "northwest": (-1, -1), "north": (0, -1), "northeast": (1, -1),
    "west":      (-1,  0),                   "east":      (1,  0),
    "southwest": (-1,  1), "south":   (0,  1), "southeast": (1,  1),
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
    A graph of Room instances.  Nodes are room.hash keys, with 'room' attribute.
    """

    def add_room(self, room: Room):
        self.add_node(room.hash, room=room)
        room.graph_ref = self

    def has_room(self, room_hash: str) -> bool:
        return room_hash in self.nodes

    def get_room(self, room_hash: str) -> Room | None:
        data = self.nodes.get(room_hash)
        return data["room"] if data else None

    def connect_rooms(self, src_hash: str, dst_hash: str):
        if src_hash in self.nodes and dst_hash in self.nodes:
            self.add_edge(src_hash, dst_hash)

    def layout_from_root(self, root_hash: str) -> dict[str, tuple[int, int]]:
        """
        Flood‐fill from root_hash, stripping any 'up'/'down' suffix so that
        e.g. 'northup' behaves like 'north'.  Stops on overlap and assigns
        grid coords on each Room.
        """
        if root_hash not in self.nodes:
            return {}

        positions: dict[str, tuple[int, int]] = {root_hash: (0, 0)}
        coord_owner: dict[tuple[int,int], str] = {(0, 0): root_hash}
        queue = collections.deque([root_hash])

        while queue:
            cur_hash = queue.popleft()
            cx, cy = positions[cur_hash]
            room = self.get_room(cur_hash)
            room.grid_x, room.grid_y = cx, cy

            for dir_txt, neigh_hash in room.links.items():
                if neigh_hash not in self.nodes:
                    continue

                # Strip vertical suffix before lookup
                base_dir = _strip_vertical_suffix(dir_txt)
                delta = _TXT_TO_DELTA.get(base_dir)
                if not delta:
                    continue
                dx, dy = delta

                # Already positioned?
                if neigh_hash in positions:
                    nx_, ny_ = positions[neigh_hash]
                    # If coords don't match expected—treat as boundary
                    if (cx + dx, cy + dy) != (nx_, ny_):
                        continue
                    else:
                        continue

                # Overlap check
                target = (cx + dx, cy + dy)
                owner = coord_owner.get(target)
                if owner and owner != neigh_hash:
                    continue

                positions[neigh_hash] = target
                coord_owner[target] = neigh_hash
                queue.append(neigh_hash)

        return positions