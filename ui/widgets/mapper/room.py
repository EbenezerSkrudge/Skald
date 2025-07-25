# core/mapper/room.py

class Room:
    def __init__(self, info: dict):
        self.hash      = info.get("hash")
        self.desc      = info.get("short", "no description")
        self.terrain   = info.get("type", "unexplored")
        self.links     = info.get("links", {})  # direction → hash

        self.icon      = None  # QGraphicsItem
        self.graph_ref = None  # MapGraph

    def __repr__(self):
        return f"<Room {self.hash}: {self.desc}>"

    @property
    def explored(self) -> bool:
        return self.terrain != "unexplored"

    def update_from_gmcp(self, info: dict):
        """Update room details from a GMCP packet."""
        self.desc    = info.get("short", self.desc)
        self.terrain = info.get("type", self.terrain)
        self.links   = info.get("links", self.links)

        if self.icon:
            self.icon.setToolTip(self.desc)
            self.icon.terrain = self.terrain
            self.icon.refresh()

    def direction_to(self, other: 'Room') -> str | None:
        """Return direction to the given room, if known."""
        return next((d for d, h in self.links.items() if h == other.hash), None)
