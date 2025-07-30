from PySide6.QtCore import QLineF, QPointF, QRectF
from PySide6.QtGui import Qt, QPen, QColor, QBrush, QTransform, QPolygonF
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsLineItem, QGraphicsRectItem, QGraphicsPolygonItem

from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE


class CardinalDirectionConnector(QGraphicsItemGroup):
    """
    A unified connector class that can represent:
        - Basic connectors
        - Connectors with an optional door (None, "open", or "closed")
        - Border connectors with arrows and hover effects.
    """

    CONNECTOR_COLOUR    = Qt.darkGray
    HOVER_COLOUR        = Qt.cyan
    BORDER_COLOUR       = QColor("orange")

    _border_pen = QPen(QColor(BORDER_COLOUR), 4)
    _connector_pen = QPen(QColor(CONNECTOR_COLOUR), 4)

    def __init__(self, icon_a, icon_b=None, target_pos=None,
                 door=None, border=False,
                 arrow_size=8, shaft_length=16,
                 line_width=4):
        """
        :param icon_a: The starting graphic icon.
        :param icon_b: The ending graphic icon (optional if using target_pos).
        :param target_pos: A fixed endpoint for the connector (optional).
        :param door: Door state: "none", "open", or "closed".
        :param border: Whether the connector is a border type.
        :param arrow_size: Arrow size (used if border=True).
        :param shaft_length: Shaft length (used if border=True).
        :param line_width: Width of the connector line.
        """
        super().__init__()

        self.icon_a = icon_a
        self.icon_b = icon_b
        self.target_pos = target_pos
        self.door_state = door
        self.border = border

        # Pens and Z-order
        if border:
            self._normal_pen = self._border_pen
        else:
            self._normal_pen = self._connector_pen

        self._hover_pen = QPen(self.HOVER_COLOUR, line_width + 1)

        self.setZValue(Z_CONNECTOR)

        # Main line for the connector
        self.line_item = QGraphicsLineItem(parent=self)
        self.line_item.setPen(self._normal_pen)

        self.shaft_length = shaft_length

        # Optional door rectangle visualization
        self.door_item = None
        if door:
            self.door_item = QGraphicsRectItem(parent=self)
            self.door_item.setZValue(Z_ROOM_SHAPE)

        # Optional border arrow
        self.arrow_item = None
        if border:
            self.arrow_item = QGraphicsPolygonItem(parent=self)
            self.arrow_item.setZValue(Z_CONNECTOR)
            self.arrow_item.setBrush(QBrush(QColor(self.BORDER_COLOUR)))
            self.arrow_item.setPen(self._normal_pen)
            self.line_item.setPen(self._normal_pen)
            self._base_arrow_poly = QPolygonF([
                QPointF(0, -arrow_size),
                QPointF(-arrow_size * 0.6, 0),
                QPointF(+arrow_size * 0.6, 0)
            ])
            self.arrow_item.setPolygon(self._base_arrow_poly)

        self.setAcceptHoverEvents(True)
        self.line_item.setAcceptHoverEvents(True)
        if self.arrow_item:
            self.arrow_item.setAcceptHoverEvents(True)
        if self.door_item:
            self.door_item.setAcceptHoverEvents(True)

        self.refresh()

    def refresh(self):
        """Update connector geometry, the door, and border visualization."""
        p1 = self.icon_a.scenePos()

        if self.icon_b:
            p2 = self.icon_b.scenePos()
        else:
            p2 = self.target_pos

        line = QLineF(p1, p2)
        length = line.length()
        angle = -line.angle()

        # Halve the line length if this is a border connector
        if self.border:
            half_length = length / 2
            line.setLength(half_length)  # Adjust the line to half its original length

        # Update the main line
        self.line_item.setLine(line)

        # Update the door item (if applicable)
        if self.door_item:
            door_width, door_height = 30, 10

            if self.border:
                # For border connectors, place the door at the end of the line
                position = line.p2()
            else:
                # For non-border connectors, place the door at the midpoint of the line
                position = line.center()

            rotation = (angle + 70) if self.door_state == "open" else (angle + 90)
            brush_color = QColor("lime" if self.door_state == "open" else "red")

            self.door_item.setRect(
                QRectF(position.x() - door_width / 2, position.y() - door_height / 2, door_width, door_height)
            )
            self.door_item.setBrush(QBrush(brush_color))

            transform = (
                QTransform()
                .translate(position.x(), position.y())
                .rotate(rotation)
                .translate(-position.x(), -position.y())
            )
            self.door_item.setTransform(transform)

        # Update the border arrow (if applicable)
        if self.arrow_item:
            if self.border and not self.door_state:  # Only show the arrow if there's no door
                self.arrow_item.setPolygon(self._base_arrow_poly)
                self.arrow_item.setRotation(angle + 90)
                self.arrow_item.setPos(line.p2())  # Place the arrow at the end of the halved line
            else:
                self.arrow_item.setPolygon(QPolygonF())  # Hide the arrow if a door exists

    def add_to_scene(self, scene):
        """Add the connector to the scene."""
        scene.addItem(self)

    def boundingRect(self):
        return self.childrenBoundingRect()

    def hoverEnterEvent(self, event):
        """Handle hover enter: Apply hover appearance."""
        self.line_item.setPen(self._hover_pen)
        if self.arrow_item:
            self.arrow_item.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Handle hover leave: Return to normal appearance."""
        self.line_item.setPen(self._normal_pen)
        if self.arrow_item:
            self.arrow_item.setPen(self._normal_pen)
        super().hoverLeaveEvent(event)
