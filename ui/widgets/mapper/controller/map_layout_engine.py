# ui/widgets/mapper/controller/map_layout_engine.py

class MapLayoutEngine:
    def __init__(self, global_graph):
        self.global_graph = global_graph
        self.local_positions = {}

    def build_local_area(self, local_graph, root_hash):
        local_graph.clear()
        self.local_positions.clear()

        if not root_hash or not self.global_graph.has_room(root_hash):
            return

        self.local_positions = self.global_graph.layout_from_root(root_hash)

        for h in self.local_positions:
            local_graph.add_room(self.global_graph.get_room(h))

        for a, b in self.global_graph.edges():
            if a in self.local_positions and b in self.local_positions:
                if not self.global_graph.is_border(a, b):
                    local_graph.connect_rooms(a, b)

    def update_positions(self, root_hash):
        if root_hash:
            self.local_positions = self.global_graph.layout_from_root(root_hash)
        else:
            self.local_positions.clear()
