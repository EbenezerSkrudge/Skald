# core/mapper/room.py

from PySide6.QtCore import QPointF
from ui.widgets.mapper.room_icon import RoomIcon

class Room:
    def __init__(self, info: dict, grid_x: int, grid_y: int):
        self.hash       = info.get("hash")
        self.desc       = info.get("short", "no description")
        self.area       = info.get("area", "unknown")
        self.terrain    = info.get("type", "unknown")
        self.links      = info.get("links", {})  # direction→hash map

        self.grid_x     = grid_x
        self.grid_y     = grid_y

        self.icon       = None  # QGraphicsItem reference
        self.graph_ref  = None  # Optional reference to MapGraph

    @property
    def position(self) -> QPointF:
        from ui.widgets.mapper.constants import GRID_SIZE
        return QPointF(self.grid_x * GRID_SIZE, self.grid_y * GRID_SIZE)

    @property
    def explored(self) -> bool:
        return self.terrain != "unexplored"

    def render(self) -> RoomIcon:
        """Create and return the visual RoomIcon."""
        self.icon = RoomIcon(
            grid_x=self.grid_x,
            grid_y=self.grid_y,
            short_desc=self.desc,
            terrain=self.terrain
        )
        return self.icon

    def update_from_gmcp(self, info: dict):
        """Refresh room details from a new GMCP packet."""
        self.desc    = info.get("short", self.desc)
        self.area    = info.get("area", self.area)
        self.terrain = info.get("type", self.terrain)
        self.links   = info.get("links", self.links)

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
