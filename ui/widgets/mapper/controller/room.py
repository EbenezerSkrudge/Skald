# core/mapper/room.py
from typing import Dict


class Room:
    __slots__ = ("hash", "desc", "terrain", "links", "icon", "graph_ref", "grid_x", "grid_y")

    def __init__(self, info: dict):
        self.hash = info.get("hash")
        self.desc = info.get("short", "no description")
        self.terrain = info.get("type", -1)
        self.links: Dict[str, str] = info.get("links", {})
        self.icon = None  # QGraphicsItem reference
        self.graph_ref = None  # Optional reference to MapGraph
        self.grid_x = 0
        self.grid_y = 0

    @property
    def explored(self) -> bool:
        return self.terrain != -1

    def update_from_gmcp(self, info: dict):
        """Refresh room details from a new GMCP packet."""
        self.desc = info.get("short", self.desc)
        self.terrain = info.get("type", self.terrain)
        self.links = info.get("links", self.links)

        if self.icon:
            self.icon.setToolTip(self.desc)
            self.icon.terrain = self.terrain
            self.icon.refresh()

    def direction_to(self, other: 'Room') -> str | None:
        """Returns the direction name from this room to another, if known."""
        for dir_name, dest_hash in self.links.items():
            if dest_hash == other.hash:
                return dir_name
        return None

    def to_dict(self) -> dict:
        return {
            "hash": self.hash,
            "short": self.desc,
            "type": self.terrain,
            "links": self.links,
            "grid_x": getattr(self, "grid_x", None),
            "grid_y": getattr(self, "grid_y", None),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Room':
        room = cls(data)
        room.grid_x = data.get("grid_x")
        room.grid_y = data.get("grid_y")
        return room
