# core/mapper/room.py

class Room:
    def __init__(self, info: dict):
        self.hash       = info.get("hash")
        self.desc       = info.get("short", "no description")
        self.terrain    = info.get("type", "unexplored")
        self.links      = info.get("links", {})  # direction→hash map

        self.icon       = None  # QGraphicsItem reference
        self.graph_ref  = None  # Optional reference to MapGraph

    @property
    def explored(self) -> bool:
        return self.terrain != "unexplored"

    def update_from_gmcp(self, info: dict):
        """Refresh room details from a new GMCP packet."""
        self.desc    = info.get("short", self.desc)
        #self.area    = info.get("area", self.area)
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
