# # ui/widgets/mapper/map_context.py
#
# from PySide6.QtWidgets import QGraphicsItemGroup
#
# class MapContext:
#     """
#     Holds all the QGraphicsItems (rooms/connectors/placeholders)
#     for one logical map layer (e.g. wilderness, a town interior, a building).
#     """
#
#     def __init__(self, context_id, scene):
#         self.id        = context_id
#         self.scene     = scene
#         self.group     = QGraphicsItemGroup()
#         self.scene.addItem(self.group)
#
#         # track your items so you can clear them if you like
#         self.rooms       = {}  # room_hash -> RoomItem
#         self.connectors  = []  # list of ConnectorItem
#         self.placeholders= []  # list of RoomItem placeholders
#
#     def add_room(self, room_item):
#         """Attach a RoomItem to this context."""
#         self.group.addToGroup(room_item)
#         self.rooms[room_item.room_hash] = room_item
#
#     def add_connector(self, connector_item):
#         """Attach a ConnectorItem to this context."""
#         self.group.addToGroup(connector_item)
#         self.connectors.append(connector_item)
#
#     def add_placeholder(self, placeholder_item):
#         """Attach an unexplored placeholder room."""
#         self.group.addToGroup(placeholder_item)
#         self.placeholders.append(placeholder_item)
#
#     def clear(self):
#         """Remove ALL items from scene and reset."""
#         for item in (*self.rooms.values(), *self.connectors, *self.placeholders):
#             self.group.removeFromGroup(item)
#             self.scene.removeItem(item)
#         self.rooms.clear()
#         self.connectors.clear()
#         self.placeholders.clear()
#
#     def set_visible(self, yes: bool):
#         self.group.setVisible(yes)