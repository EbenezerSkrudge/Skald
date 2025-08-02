# ui/widgets/mapper/controller/map_state_manager.py

import os
import pickle
from ui.widgets.mapper.map_graph import MapGraph
from ui.widgets.mapper.utils import split_suffix
from ui.widgets.mapper.constants import TEXT_TO_NUM


class MapStateManager:
    def __init__(self, profile_path=None):
        self.profile_path = profile_path or os.path.expanduser("~/.skald/default")
        self.map_file_path = os.path.join(self.profile_path, "map.pickle")
        self.global_graph = self._load_map() or MapGraph()
        self.local_graph = MapGraph()

        self.current_room = None
        self.prev_links = {}

    def _load_map(self):
        try:
            if os.path.exists(self.map_file_path):
                with open(self.map_file_path, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"Error loading map: {e}")
        return None

    def save_map(self):
        try:
            os.makedirs(self.profile_path, exist_ok=True)
            tmp_path = self.map_file_path + ".tmp"
            with open(tmp_path, "wb") as f:
                pickle.dump(self.global_graph, f, protocol=pickle.HIGHEST_PROTOCOL) # type: ignore
            os.replace(tmp_path, self.map_file_path)
        except Exception as e:
            print(f"Error saving map: {e}")

    def update_links_before_change(self):
        if self.current_room and self.global_graph.has_room(self.current_room):
            self.prev_links = dict(self.global_graph.get_room(self.current_room).links)
        else:
            self.prev_links.clear()

    def add_or_update_room(self, info):
        self.global_graph.add_or_update_room(info, exit_types=info.get("exits", {}))
        self.current_room = info["hash"]

    def get_move_code(self, new_hash):
        if not self.current_room:
            return None
        direction = next((d for d, dst in self.prev_links.items() if dst == new_hash), None)
        return TEXT_TO_NUM.get(split_suffix(direction)[0]) if direction else None
