# ui/widgets/mapper/connector_item.py

import math
from PySide6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsPolygonItem
)
from PySide6.QtGui import (
    QPen, QBrush, QLinearGradient, QColor, QTransform, QPolygonF, Qt
)
from PySide6.QtCore import QRectF, QPointF, QLineF

from ui.widgets.mapper.constants import Z_CONNECTOR, Z_ROOM_SHAPE, Z_ROOM_ICON
from game.terrain import TERRAIN_TYPES
from ui.widgets.mapper.utils import shorten_line, create_arrowhead


class ConnectorItem(QGraphicsLineItem):
    """
    A simple line between two RoomIcon.scenePos() points,
    accepts hover events to highlight when under the cursor.
    """

    def __init__(self, icon_a, icon_b, color=Qt.darkGray, width=5):
        super().__init__()
        self.icon_a = icon_a
        self.icon_b = icon_b

        # Normal vs hover pens
        self._normal_pen = QPen(QColor(color), width)
        self._hover_pen  = QPen(QColor(Qt.cyan), width + 1)

        self.setPen(self._normal_pen)
        self.setZValue(Z_CONNECTOR)

        # Enable hover events
        self.setAcceptHoverEvents(True)

        # Initial draw
        self.refresh()

    def refresh(self):
        p1 = self.icon_a.scenePos()
        p2 = self.icon_b.scenePos()
        self.setLine(QLineF(p1, p2))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)
        super().hoverLeaveEvent(event)

    def add_to_scene(self, scene):
        scene.addItem(self)


class BorderConnectorItem(QGraphicsPolygonItem):
    """
    A little arrow + shaft indicating a 'border' link.
    Also highlights on hover.
    """

    def __init__(self, icon_a, icon_b=None, target_pos=None,
                 arrow_size=8, shaft_length=16, color=Qt.yellow):
        super().__init__()
        self.icon_a     = icon_a
        self.icon_b     = icon_b
        self.target_pos = target_pos
        self.arrow_size = arrow_size
        self.shaft_len  = shaft_length

        # Pens for normal vs hover
        self._normal_pen = QPen(QColor(color), 4)
        self._hover_pen  = QPen(QColor(Qt.cyan), 5)

        self.setPen(self._normal_pen)
        self.setBrush(QBrush(QColor(color)))
        self.setZValue(Z_CONNECTOR)

        # Build the shaft as a child line item
        self.shaft = QGraphicsLineItem(self)
        self.shaft.setPen(self._normal_pen)
        self.shaft.setZValue(Z_CONNECTOR - 1)

        # Build the arrowhead polygon (pointing up at local origin)
        h = arrow_size
        w = arrow_size * 0.6
        self._base_poly = QPolygonF([
            QPointF(0, -h),
            QPointF(-w, 0),
            QPointF( w, 0),
        ])
        self.setPolygon(self._base_poly)

        # Enable hover events
        self.setAcceptHoverEvents(True)
        self.shaft.setAcceptHoverEvents(True)

        # Initial draw/position
        self.refresh()

    def refresh(self):
        # Anchor and target positions in scene coords
        p1 = self.icon_a.scenePos()
        p2 = self.target_pos or self.icon_b.scenePos()

        # Midpoint for placing the arrowhead
        mid = QPointF((p1.x() + p2.x()) / 2,
                      (p1.y() + p2.y()) / 2)

        # Compute rotation angle (0° = east, 90° = north)
        angle = QLineF(p1, p2).angle()

        # Rotate & move arrowhead
        self.setRotation(-angle + 90)
        self.setPos(mid)

        # Draw shaft *behind* the arrow
        # Local coords: tip at (0,0), shaft extends further back (positive Y)
        tip  = QPointF(0, 0)
        back = QPointF(0, self.shaft_len)
        self.shaft.setLine(QLineF(tip, back))

    def hoverEnterEvent(self, event):
        self.setPen(self._hover_pen)
        self.shaft.setPen(self._hover_pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self._normal_pen)
        self.shaft.setPen(self._normal_pen)
        super().hoverLeaveEvent(event)

    def add_to_scene(self, scene):
        scene.addItem(self)


class DoorConnectorItem(ConnectorItem):
    """
    A ConnectorItem with a door‐symbol overlay (green=open, red=closed).
    """

    def __init__(self, room_a, room_b, door_open: bool = True):
        # 1) remember door state
        self.door_open = door_open

        # 2) create a 'dummy' symbol_item so refresh() in the base class won't fail
        self.symbol_item = QGraphicsRectItem()
        # don't set a parent yet—that will happen after super().__init__

        # 3) init the line+base refresh
        super().__init__(room_a, room_b)

        # 4) now that the QGraphicsLineItem is fully built, re-parent the rect
        self.symbol_item.setParentItem(self)
        self.symbol_item.setZValue(Z_ROOM_SHAPE)

        # 5) final refresh to size & rotate the door‐rect correctly
        self.refresh()

    def refresh(self):
        # reposition the line
        super().refresh()

        # compute midpoint
        line = self.line()
        mid = QPointF(
            (line.x1() + line.x2()) / 2,
            (line.y1() + line.y2()) / 2
        )

        # update the door‐rect
        rect = QRectF(mid.x() - 15, mid.y() - 3, 30, 6)
        self.symbol_item.setRect(rect)

        # rotation: align with the line
        angle = math.degrees(math.atan2(
            line.y2() - line.y1(),
            line.x2() - line.x1()
        ))
        rotation = angle + (45 if self.door_open else 90)

        # color by open/closed
        fill = QColor("lime") if self.door_open else QColor("red")
        penc = QColor("white") if self.door_open else QColor("black")
        self.symbol_item.setBrush(QBrush(fill))
        self.symbol_item.setPen(QPen(penc, 1))

        # rotate around center
        xf = (
            QTransform()
              .translate(mid.x(), mid.y())
              .rotate(rotation)
              .translate(-mid.x(), -mid.y())
        )
        self.symbol_item.setTransform(xf)


class DoorBorderConnectorItem(QGraphicsItemGroup):
    """
    A border‐connector that draws a shortened shaft plus a centered
    door‐rect (green=open, red=closed). The group’s local origin
    is always the midpoint, so it never drifts.
    """

    def __init__(
        self,
        icon_a,
        icon_b=None,
        target_pos: QPointF = None,
        door_open: bool = True,
        line_color=Qt.yellow,
        line_width=6,
        door_size=(30, 6),
        shaft_shrink: float = 20.0
    ):
        super().__init__()
        self.icon_a       = icon_a
        self.icon_b       = icon_b
        self.target_pos   = target_pos
        self.door_open    = door_open
        self.door_w, self.door_h = door_size
        self.shaft_shrink = shaft_shrink

        # Shaft line
        self.line_item = QGraphicsLineItem(parent=self)
        pen = QPen(QColor(line_color), line_width)
        self.line_item.setPen(pen)
        self.line_item.setZValue(Z_CONNECTOR)

        # Door rectangle
        self.rect_item = QGraphicsRectItem(parent=self)
        fill_color = QColor("lime") if door_open else QColor("red")
        border_color = QColor("white") if door_open else QColor("black")
        self.rect_item.setBrush(QBrush(fill_color))
        self.rect_item.setPen(QPen(border_color, 1))
        self.rect_item.setZValue(Z_ROOM_SHAPE)

        # Draw once
        self.refresh()

    def refresh(self):
        # 1) Calculate endpoints in scene coords
        p1 = self.icon_a.scenePos()
        p2 = self.target_pos or self.icon_b.scenePos()

        # 2) Midpoint
        mid = QPointF((p1.x() + p2.x()) / 2,
                      (p1.y() + p2.y()) / 2)

        # 3) Distance & half-length
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = (dx * dx + dy * dy) ** 0.5
        raw_half = length / 2

        # 4) Shrink shaft ends
        half = max(raw_half - self.shaft_shrink, 0)

        # 5) Position & rotate group so +X aligns with the line
        angle = QLineF(p1, p2).angle()  # 0°=east, 90°=north
        self.setPos(mid)
        self.setRotation(-angle)

        # 6) Draw shortened shaft from local (–half, 0) to (+half, 0)
        self.line_item.setLine(
            QLineF(QPointF(-half, 0), QPointF(+half, 0))
        )

        # 7) Draw door rect centered at local origin
        rect = QRectF(-self.door_w / 2, -self.door_h / 2,
                      self.door_w, self.door_h)
        self.rect_item.setRect(rect)

        # 8) Rotate the door‐rect across the shaft:
        #    closed = 90°, open = 45°
        door_angle = 90 if not self.door_open else 45
        self.rect_item.setRotation(door_angle)

    def add_to_scene(self, scene):
        scene.addItem(self)


class NonCardinalDirectionTag(QGraphicsItemGroup):
    """
    Renders in/out or up/down arrows around an icon.
    `icon` should be a QGraphicsItem you can query for its scene‐center.
    `directions` is a list like ['in','up'] etc.
    """
    def __init__(self, icon, directions: list[str]):
        super().__init__()

        # compute the icon’s center in SCENE coords
        br = icon.boundingRect()
        center_local = br.center()
        center_scene = icon.mapToScene(center_local)
        cx, cy = center_scene.x(), center_scene.y()

        orange   = QColor("orange")
        arrow_pen = QPen(orange, 3)
        dash_pen  = QPen(orange, 3)

        # 1) the in/out bubble + arrows
        if any(d in directions for d in ("in", "out")):
            io = QGraphicsItemGroup(self)
            circ = QGraphicsEllipseItem(QRectF(-6, -6, 12, 12))
            circ.setPen(QPen(orange, 2))
            io.addToGroup(circ)

            for d in ("in", "out"):
                if d not in directions:
                    continue
                # in: arrow pointing into the bubble
                start = QPointF(7, 7)   if d == "in"  else QPointF(0, 0)
                end   = QPointF(-2, -2) if d == "in"  else QPointF(9, 9)
                se = shorten_line(start, end, 2)
                shaft = QGraphicsLineItem(start.x(), start.y(), se.x(), se.y())
                shaft.setPen(arrow_pen)
                io.addToGroup(shaft)
                io.addToGroup(create_arrowhead(start, end, orange))

            io.setPos(cx + 30, cy + 11)
            io.setZValue(Z_ROOM_ICON)

        # 2) the up/down dashes + arrows
        if any(d in directions for d in ("up", "down")):
            ud = QGraphicsItemGroup(self)
            # little dashes at left/right
            for x in (-5, 6):
                dash = QGraphicsLineItem(x - 1, 0, x, 0)
                dash.setPen(dash_pen)
                ud.addToGroup(dash)

            for d in ("up", "down"):
                if d not in directions:
                    continue
                # up: arrow pointing upward, down: arrow pointing downward
                y = 6
                start = QPointF(0,  y)     if d == "up"   else QPointF(0, -y)
                end   = QPointF(0, -y - 2) if d == "up"   else QPointF(0, y + 2)
                se = shorten_line(start, end, 2)
                shaft = QGraphicsLineItem(start.x(), start.y(), se.x(), se.y())
                shaft.setPen(arrow_pen)
                ud.addToGroup(shaft)
                ud.addToGroup(create_arrowhead(start, end, orange))

            ud.setPos(cx + 31, cy - 12)
            ud.setZValue(Z_ROOM_ICON)

        self.setZValue(Z_ROOM_ICON)
