# ui/widgets/mapper/controller/map_controller.py

from PySide6.QtCore import QObject, Signal, QTimer, QEvent

from ui.widgets.mapper.controller.map_layout_engine import MapLayoutEngine
from ui.widgets.mapper.controller.map_renderer import MapRenderer
from ui.widgets.mapper.controller.map_state_manager import MapStateManager


class MapController(QObject):
    mapUpdated = Signal()

    def __init__(self, mapper_widget, profile_path=None):
        super().__init__()
        self.map = mapper_widget
        self.state = MapStateManager(profile_path)
        self.layout = MapLayoutEngine(self.state.global_graph)
        self.renderer = MapRenderer(mapper_widget, self.state)

        self._save_timer = QTimer(self, singleShot=True)
        self._save_timer.timeout.connect(self.state.save_map)

        self.map.horizontalScrollBar().valueChanged.connect(self.render)
        self.map.verticalScrollBar().valueChanged.connect(self.render)
        self.map.viewport().installEventFilter(self)

    def cleanup(self):
        try:
            self.map.viewport().removeEventFilter(self)
            self.map.horizontalScrollBar().valueChanged.disconnect(self.render)
            self.map.verticalScrollBar().valueChanged.disconnect(self.render)
        except AttributeError:
            pass

    def schedule_save(self):
        self._save_timer.start(1000)

    def eventFilter(self, obj, event):
        if obj == self.map.viewport() and event.type() == QEvent.Resize:
            try:
                self.render()
            except RuntimeError:
                pass
        return super().eventFilter(obj, event)

    def on_room_info(self, info: dict):
        room_hash = info.get("hash")
        if not room_hash:
            return

        self.state.update_links_before_change()
        self.state.add_or_update_room(info)
        self.layout.build_local_area(self.state.local_graph, room_hash)
        self.renderer.update_marker(room_hash, self.state.get_move_code(room_hash))
        self.render()
        self.mapUpdated.emit()
        self.schedule_save()

    def render(self):
        self.layout.update_positions(self.state.current_room)
        self.renderer.render(self.state.current_room, self.layout.local_positions)
        self.mapUpdated.emit()
