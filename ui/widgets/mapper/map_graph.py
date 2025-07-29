# ui/widgets/mapper/map_graph.py

import collections
import pickle
from pathlib import Path

import networkx as nx

from ui.widgets.mapper.constants import TEXT_TO_DELTA
from ui.widgets.mapper.room import Room


def _strip_vertical_suffix(direction: str) -> str:
    direction = direction.lower()
    if direction.endswith("up"):
        return direction[:-2]
    if direction.endswith("down"):
        return direction[:-4]
    return direction


class MapGraph(nx.Graph):
    """
    A graph of Room instances. Nodes keyed by room.hash.
    Edges may include:
      - 'border' (bool): prevents traversal
      - 'door_open' (bool): open (True), closed (False), or None
    """

    def add_room(self, room: Room):
        if room.hash and room.hash not in self.nodes:
            self.add_node(room.hash, room=room)
            room.graph_ref = self

    def add_or_update_room(self, info: dict, exit_types: dict[str, int] | None = None):
        exit_types = exit_types or {}
        room_hash = info.get("hash")
        if not room_hash:
            return

        # Update or create Room
        room = self.nodes.get(room_hash, {}).get("room")
        if room:
            room.desc = info.get("short", room.desc)
            room.terrain = info.get("type", room.terrain)
            room.links = info.get("links", room.links)
        else:
            room = Room(info)
            self.add_room(room)

        # Link neighbors
        for dir_txt, dest_hash in (room.links or {}).items():
            if not dest_hash:
                continue
            if dest_hash not in self.nodes:
                self.add_room(Room({"hash": dest_hash}))

            existing = self.get_edge_data(room_hash, dest_hash, default={})
            had_edge = bool(existing)
            border = existing.get("border", False)
            door_open = existing.get("door_open")

            # Handle GMCP exit type code
            match exit_types.get(dir_txt):
                case 101:  # open door
                    door_open = True
                    if not had_edge:
                        border = False
                case -101:  # closed door
                    door_open = False
                    if not had_edge:
                        border = True

            self.connect_rooms(room_hash, dest_hash, border=border, door_open=door_open)

    def has_room(self, room_hash: str) -> bool:
        return room_hash in self.nodes

    def get_room(self, room_hash: str) -> Room | None:
        return self.nodes.get(room_hash, {}).get("room")

    def connect_rooms(self, src: str, dst: str, border: bool = False, door_open: bool | None = None):
        if src in self.nodes and dst in self.nodes:
            attrs = {"border": border}
            if door_open is not None:
                attrs["door_open"] = door_open
            self.add_edge(src, dst, **attrs)

    def set_border(self, a: str, b: str, border: bool = True):
        if self.has_edge(a, b):
            self.add_edge(a, b, border=border)

    def is_border(self, a: str, b: str) -> bool:
        return self.has_edge(a, b) and self[a][b].get("border", False)

    def layout_from_root(self, root_hash: str) -> dict[str, tuple[int, int]]:
        if root_hash not in self.nodes:
            return {}

        positions = {root_hash: (0, 0)}
        coord_owner = {(0, 0): root_hash}
        queue = collections.deque([root_hash])

        while queue:
            current = queue.popleft()
            x, y = positions[current]
            room = self.get_room(current)
            room.grid_x, room.grid_y = x, y

            for dir_txt, neighbor in (room.links or {}).items():
                if not neighbor or neighbor not in self.nodes:
                    continue
                if self.is_border(current, neighbor):
                    continue

                delta = TEXT_TO_DELTA.get(_strip_vertical_suffix(dir_txt))
                if not delta:
                    continue

                neighbour_x, neighbor_y = x + delta[0], y + delta[1]
                if neighbor in positions:
                    continue
                if coord_owner.get((neighbour_x, neighbor_y), neighbor) != neighbor:
                    continue

                positions[neighbor] = (neighbour_x, neighbor_y)
                coord_owner[(neighbour_x, neighbor_y)] = neighbor
                queue.append(neighbor)

        return positions

    def save_to_file(self, path: str | Path):
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL) # type: ignore

    @staticmethod
    def load_from_file(path: str | Path) -> "MapGraph":
        with open(path, "rb") as f:
            return pickle.load(f)
