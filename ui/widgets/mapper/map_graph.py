# ui/widgets/mapper/map_graph.py

import collections
import networkx as nx
from ui.widgets.mapper.room import Room

# Direction → (dx, dy)
_TXT_TO_DELTA = {
    "northwest": (-1, -1), "north": ( 0, -1), "northeast": ( 1, -1),
    "west":      (-1,  0),                         "east": ( 1,  0),
    "southwest": (-1,  1), "south": ( 0,  1), "southeast": ( 1,  1),
}


class MapGraph(nx.Graph):
    """
    A graph of Room instances.  Nodes are room.hash keys, with 'room' attribute.
    """

    def __init__(self):
        super().__init__()

    def add_room(self, room: Room):
        """
        Insert a Room into the graph.  If the hash already exists, updates its data.
        """
        self.add_node(room.hash, room=room)
        room.graph_ref = self

    def has_room(self, room_hash: str) -> bool:
        return room_hash in self.nodes

    def get_room(self, room_hash: str) -> Room | None:
        data = self.nodes.get(room_hash)
        return data["room"] if data else None

    def remove_room(self, room_hash: str):
        if room_hash in self.nodes:
            self.remove_node(room_hash)

    def connect_rooms(self, src_hash: str, dst_hash: str):
        """
        Create an undirected edge between two rooms.
        """
        if src_hash in self.nodes and dst_hash in self.nodes:
            self.add_edge(src_hash, dst_hash)

    def layout_from_root(self, root_hash: str) -> dict[str, tuple[int, int]]:
        """
        Breadth-first layout from root_hash:
        - Stops on overlap (distinct rooms wanting same coords)
        - Assigns grid_x, grid_y on each Room
        Returns a map of room_hash -> (grid_x, grid_y)
        """
        if root_hash not in self.nodes:
            return {}

        positions: dict[str, tuple[int, int]] = {root_hash: (0, 0)}
        coord_owner: dict[tuple[int,int], str] = {(0, 0): root_hash}
        queue = collections.deque([root_hash])

        while queue:
            current = queue.popleft()
            cx, cy = positions[current]
            room: Room = self.nodes[current]["room"]

            # Set the Room’s coordinates
            room.grid_x, room.grid_y = cx, cy

            # Traverse each exit link
            for dir_txt, neigh_hash in room.links.items():
                if neigh_hash not in self.nodes:
                    continue

                # Already positioned?
                if neigh_hash in positions:
                    # If it maps to a different coord, that’s a boundary; skip
                    nx_, ny_ = positions[neigh_hash]
                    dx_, dy_ = _TXT_TO_DELTA.get(dir_txt, (0, 0))
                    if (cx + dx_, cy + dy_) != (nx_, ny_):
                        continue
                    # otherwise it’s the same room revisiting—ignore
                    continue

                delta = _TXT_TO_DELTA.get(dir_txt)
                if not delta:
                    continue
                dx, dy = delta
                nx_, ny_ = cx + dx, cy + dy

                # Overlap check: if a *different* room already owns that coord
                owner = coord_owner.get((nx_, ny_))
                if owner and owner != neigh_hash:
                    # Hit the boundary—don't traverse beyond
                    continue

                # Accept placement
                positions[neigh_hash] = (nx_, ny_)
                coord_owner[(nx_, ny_)] = neigh_hash
                queue.append(neigh_hash)

        return positions