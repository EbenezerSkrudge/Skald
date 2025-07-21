# ui/widgets/mapper/room_item.py

from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsItem, QMenu, QInputDialog, QMessageBox,
)
from PySide6.QtGui import QBrush, QPen, QColor, Qt
from PySide6.QtCore import QPointF

from ui.widgets.mapper.constants import (
    Z_ROOM_SHAPE,
    Z_ROOM_ICON,
    GRID_SIZE,
    ROOM_SIZE,
)


class RoomItem(QGraphicsItemGroup):
    def __init__(self, grid_x: int, grid_y: int, short_desc: str, color: QColor, explored: bool = True):
        super().__init__()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.pos = QPointF(grid_x * GRID_SIZE, grid_y * GRID_SIZE)
        self.short_desc = short_desc
        self.color = color
        self.explored = explored
        self.size = ROOM_SIZE

        self.setZValue(Z_ROOM_SHAPE + 1)
        self.setToolTip(short_desc)
        self._build_visuals()

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.RightButton)

    def _build_visuals(self):
        # Clear previous visuals
        for child in self.childItems():
            self.removeFromGroup(child)
            child.setParentItem(None)

        half = self.size / 2
        x, y = self.pos.x() - half, self.pos.y() - half

        # Core shape
        if self.explored:
            shape = QGraphicsRectItem(x, y, self.size, self.size)
            shape.setBrush(QBrush(self.color))
        else:
            shape = QGraphicsEllipseItem(x, y, self.size, self.size)
            shape.setBrush(QBrush(QColor("#555")))
            shape.setPen(QPen(QColor("darkgray"), 1))

            icon = QGraphicsTextItem("?")
            font = icon.font()
            font.setPointSizeF(self.size * 0.5)
            font.setBold(True)
            icon.setFont(font)
            icon.setDefaultTextColor(QColor("yellow"))

            br = icon.boundingRect()
            icon.setPos(self.pos.x() - br.width() / 2, self.pos.y() - br.height() / 2)
            icon.setZValue(Z_ROOM_ICON)
            self.addToGroup(icon)

        shape.setZValue(Z_ROOM_SHAPE)
        self.addToGroup(shape)

        # 🔲 Selection overlay
        if self.isSelected():
            border = QGraphicsRectItem(x - 2, y - 2, self.size + 4, self.size + 4)
            border.setPen(QPen(QColor("cyan"), 2))
            border.setBrush(Qt.NoBrush)
            border.setZValue(Z_ROOM_ICON + 1)
            self.addToGroup(border)

            overlay = QGraphicsRectItem(x, y, self.size, self.size)
            overlay.setBrush(QBrush(QColor(0, 255, 255, 60)))  # Light cyan with alpha
            overlay.setPen(Qt.NoPen)
            overlay.setZValue(Z_ROOM_ICON)  # Just above shape but below label/icon
            self.addToGroup(overlay)

    def center(self) -> QPointF:
        return self.pos

    def get_color(self) -> QColor:
        return self.color

    def set_explored(self, explored: bool):
        self.explored = explored
        self._build_visuals()

    def contextMenuEvent(self, event):
        selected_rooms = [
            item for item in self.scene().selectedItems()
            if isinstance(item, RoomItem)
        ]
        if not selected_rooms:
            selected_rooms = [self]  # fallback if nothing else is selected

        menu = QMenu()
        area_label = f"Set Area for {len(selected_rooms)} room(s)"
        delete_label = f"Delete {len(selected_rooms)} room(s)"

        set_area_action = menu.addAction(area_label)
        delete_action = menu.addAction(delete_label)

        action = menu.exec(event.screenPos())

        if action == set_area_action:
            self._prompt_bulk_area_change(selected_rooms)

        if action == delete_action:
            self._prompt_bulk_delete(selected_rooms)

    def _prompt_set_area(self):
        text, ok = QInputDialog.getText(None, "Set Room Area", "Enter new area name:")
        if ok and text.strip():
            self._apply_area_change(text.strip())

    def _apply_area_change(self, new_area: str):
        if hasattr(self.scene(), "controller"):
            hash_id = self.scene().controller.find_room_hash(self)
            if hash_id:
                self.scene().controller.set_room_area(hash_id, new_area)

    def _prompt_bulk_area_change(self, room_items):
        text, ok = QInputDialog.getText(None, "Set Area", f"Enter new area name for {len(room_items)} rooms:")
        if ok and text.strip():
            controller = getattr(self.scene(), "controller", None)
            if controller:
                for item in room_items:
                    room_hash = controller.find_room_hash(item)
                    if room_hash:
                        controller.set_room_area(room_hash, text.strip())

    def _prompt_bulk_delete(self, room_items):
        confirm = QMessageBox.question(
            None,
            "Confirm Room Deletion",
            f"Are you sure you want to delete {len(room_items)} room(s)? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        controller = getattr(self.scene(), "controller", None)
        if controller:
            for item in room_items:
                room_hash = controller.find_room_hash(item)
                if room_hash:
                    controller.delete_room(room_hash)

    def itemChange(self, change, value):
        if change in (
                QGraphicsItem.ItemSelectedChange,
                QGraphicsItem.ItemSelectedHasChanged
        ):
            self._build_visuals()
        return super().itemChange(change, value)

