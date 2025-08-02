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
      - 'border'   (bool): prevents traversal
      - 'door'     (str): "open", "closed", or None
      - 'exit_val' (int): raw GMCP exit type (100=road, 104=path, 101=open door, -101=closed door, etc.)
    """

    def add_room(self, room: Room):
        if room.hash and room.hash not in self.nodes:
            self.add_node(room.hash, room=room)
            room.graph_ref = self

    def add_or_update_room(
        self,
        info: dict,
        exit_types: dict[str, int] | None = None
    ):
        exit_types = exit_types or {}
        room_hash = info.get("hash")
        if not room_hash:
            return

        # Update or create the Room node
        existing_node = self.nodes.get(room_hash, {})
        room = existing_node.get("room")
        if room:
            room.desc = info.get("short", room.desc)
            room.terrain = info.get("type", room.terrain)
            room.links = info.get("links", room.links)
        else:
            room = Room(info)
            self.add_room(room)

        # Link neighbors with updated attributes
        for dir_txt, dest_hash in (room.links or {}).items():
            if not dest_hash:
                continue
            # Ensure the neighbor node exists
            if dest_hash not in self.nodes:
                self.add_room(Room({"hash": dest_hash}))

            # Retrieve existing edge data, if any
            existing = self.get_edge_data(room_hash, dest_hash, default={})
            had_edge = bool(existing)
            border = existing.get("border", False)
            door = existing.get("door", None)

            # Read the raw exit code for this direction
            code = exit_types.get(dir_txt)
            exit_val = int(code) if code is not None else None

            # GMCP codes for doors
            if exit_val == 101:
                door = "open"
                if not had_edge:
                    border = False
            elif exit_val == -101:
                door = "closed"
                if not had_edge:
                    border = True

            # For roads (100) and paths (104), we leave door/border as-is,
            # but we carry exit_val through to visualization.
            # Exit_val is passed below via connect_rooms.

            self.connect_rooms(
                src=room_hash,
                dst=dest_hash,
                border=border,
                door=door,
                exit_val=exit_val
            )

    def has_room(self, room_hash: str) -> bool:
        return room_hash in self.nodes

    def get_room(self, room_hash: str) -> Room | None:
        node = self.nodes.get(room_hash, {})
        return node.get("room")

    def connect_rooms(
        self,
        src: str,
        dst: str,
        border: bool = False,
        door: str | None = None,
        exit_val: int | None = None
    ):
        """
        Add or update an edge between src and dst with:
          - border flag
          - optional door state
          - optional exit_val for roads/paths/doors
        """
        if src in self.nodes and dst in self.nodes:
            attrs: dict[str, object] = {"border": border}
            if door is not None:
                attrs["door"] = door
            if exit_val is not None:
                attrs["exit_val"] = exit_val
            self.add_edge(src, dst, **attrs)

    def set_border(self, a: str, b: str, border: bool = True):
        if self.has_edge(a, b):
            # preserve existing door and exit_val
            existing = self.get_edge_data(a, b)
            door = existing.get("door")
            exit_val = existing.get("exit_val")
            self.connect_rooms(a, b, border=border, door=door, exit_val=exit_val)

    def is_border(self, a: str, b: str) -> bool:
        return self.has_edge(a, b) and self[a][b].get("border", False)

    def layout_from_root(self, root_hash: str) -> dict[str, tuple[int, int]]:
        if root_hash not in self.nodes:
            return {}

        positions: dict[str, tuple[int, int]] = {root_hash: (0, 0)}
        coord_owner: dict[tuple[int, int], str] = {(0, 0): root_hash}
        queue = collections.deque([root_hash])

        while queue:
            current = queue.popleft()
            x, y = positions[current]
            room = self.get_room(current)
            room.grid_x, room.grid_y = x, y

            for dir_txt, neighbour in (room.links or {}).items():
                if not neighbour or neighbour not in self.nodes:
                    continue
                if self.is_border(current, neighbour):
                    continue

                delta = TEXT_TO_DELTA.get(_strip_vertical_suffix(dir_txt))
                if not delta:
                    continue

                neighbour_x, neighbour_y = x + delta[0], y + delta[1]
                if neighbour in positions:
                    continue
                if coord_owner.get((neighbour_x, neighbour_y), neighbour) != neighbour:
                    continue

                positions[neighbour] = (neighbour_x, neighbour_y)
                coord_owner[(neighbour_x, neighbour_y)] = neighbour
                queue.append(neighbour)

        return positions

    def save_to_file(self, path: str | Path):
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)  # type: ignore

    @staticmethod
    def load_from_file(path: str | Path) -> "MapGraph":
        with open(path, "rb") as f:
            return pickle.load(f)