# ui/widgets/console/input_bar.py

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QTextCursor, QKeyEvent, QShortcut, QKeySequence
from PySide6.QtWidgets import QTextEdit, QSplitter, QWidget, QVBoxLayout

from core.config import FREEZE_PANE_MIN_HEIGHT
from ui.style import get_mono_font


class SplitConsoleDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Ensure we can receive key events
        self.setFocusPolicy(Qt.StrongFocus)

        # ─── Historical View (hidden until wheel-up or Ctrl+Up) ───
        self.historical_view = QTextEdit()
        self.historical_view.setFont(get_mono_font())
        self.historical_view.setReadOnly(True)
        self.historical_view.setLineWrapMode(QTextEdit.WidgetWidth)
        self.historical_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.historical_view.setVisible(False)
        self._user_has_scrolled = False

        QShortcut(QKeySequence("Ctrl+Up"), self).activated.connect(self._scroll_up_trigger)
        QShortcut(QKeySequence("Ctrl+Down"), self).activated.connect(self._scroll_down_trigger)

        # ─── Live View (always visible, auto-scrolls) ───
        self.live_view = QTextEdit()
        self.live_view.setFont(get_mono_font())
        self.live_view.setReadOnly(True)
        self.live_view.setLineWrapMode(QTextEdit.WidgetWidth)
        self.live_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.live_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.live_view.setMinimumHeight(FREEZE_PANE_MIN_HEIGHT)

        # Trim the phantom carriage-return line
        line_h = self.live_view.fontMetrics().lineSpacing()
        self.live_view.setViewportMargins(0, 0, 0, -line_h)

        # ─── Document Sharing ───
        doc = self.historical_view.document()
        self.live_view.setDocument(doc)
        doc.contentsChanged.connect(self._keep_live_view_visible)

        # ─── Event Filters ───
        self.live_view.viewport().installEventFilter(self)
        self.historical_view.viewport().installEventFilter(self)

        # ─── Splitter Setup ───
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.historical_view)
        self.splitter.addWidget(self.live_view)
        self.splitter.setHandleWidth(3)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStyleSheet("""
            QSplitter::handle { background-color: #444; }
            QSplitter::handle:hover { background-color: #666; }
            QSplitter::handle:horizontal { width: 6px; }
            QSplitter::handle:vertical { height: 6px; }
        """)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        self._adjusting_splitter = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

    def _keep_live_view_visible(self):
        sb = self.live_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_splitter_moved(self, pos: int, index: int):
        if self._adjusting_splitter:
            return
        line_h = self.historical_view.fontMetrics().lineSpacing()
        snapped = round(pos / line_h) * line_h
        self._adjusting_splitter = True
        QTimer.singleShot(0, lambda: self._finalize_splitter_snap(snapped, index))

    def _finalize_splitter_snap(self, snapped: int, index: int):
        self.splitter.moveSplitter(snapped, index)
        self._adjusting_splitter = False

    def _align_historical_to_live_top(self):
        # scroll so bottom of history aligns with top of live view
        line_h = self.live_view.fontMetrics().lineSpacing()
        offset = self.live_view.height() + line_h
        vbar = self.historical_view.verticalScrollBar()
        QTimer.singleShot(0, lambda: vbar.setValue(vbar.maximum() - offset))

    def echo_html(self, html: str):
        vbar = self.historical_view.verticalScrollBar()
        old = vbar.value()
        cursor = self.historical_view.textCursor()
        if not self._user_has_scrolled:
            cursor.movePosition(QTextCursor.End)
            self.historical_view.setTextCursor(cursor)
            self.historical_view.insertHtml(html)
            QTimer.singleShot(0, lambda: self._restore_scrolls(True, old))
        else:
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.End)
            cursor.insertHtml(html)
            cursor.endEditBlock()

    def _restore_scrolls(self, was_at_bottom: bool, old_pos: int):
        vbar = self.historical_view.verticalScrollBar()
        vbar.setValue(vbar.maximum() if was_at_bottom else old_pos)

    # ─── New keyboard support ───
    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Up:
                self._scroll_up_trigger()
                return
            if event.key() == Qt.Key_Down:
                self._scroll_down_trigger()
                return
        super().keyPressEvent(event)

    def _scroll_up_trigger(self):
        vsb = self.historical_view.verticalScrollBar()
        line_h = self.historical_view.fontMetrics().lineSpacing()
        if not self._user_has_scrolled:
            self._user_has_scrolled = True
            self.historical_view.setVisible(True)
            QTimer.singleShot(0, self._align_historical_to_live_top)
        else:
            vsb.setValue(vsb.value() - line_h)

    def _scroll_down_trigger(self):
        if self._user_has_scrolled:
            vsb = self.historical_view.verticalScrollBar()
            line_h = self.historical_view.fontMetrics().lineSpacing()
            vsb.setValue(vsb.value() + line_h)
            phantom = line_h
            thresh = vsb.maximum() - (self.live_view.height() + phantom)
            if vsb.value() >= thresh:
                self._user_has_scrolled = False
                self.historical_view.setVisible(False)

    def eventFilter(self, obj, event):
        match event.type():
            case QEvent.Wheel if obj in (self.live_view.viewport(),
                                         self.historical_view.viewport()):
                vsb = self.historical_view.verticalScrollBar()
                line_h = self.historical_view.fontMetrics().lineSpacing()
                delta = event.angleDelta().y()
                if delta > 0:
                    # mouse-wheel up
                    if not self._user_has_scrolled:
                        self._user_has_scrolled = True
                        self.historical_view.setVisible(True)
                        QTimer.singleShot(0, self._align_historical_to_live_top)
                    else:
                        vsb.setValue(vsb.value() - line_h)
                else:
                    # mouse-wheel down
                    if self._user_has_scrolled:
                        vsb.setValue(vsb.value() + line_h)
                        phantom = line_h
                        thresh = vsb.maximum() - (
                                self.live_view.height() + phantom
                        )
                        if vsb.value() >= thresh:
                            self._user_has_scrolled = False
                            self.historical_view.setVisible(False)
                return True

            case QEvent.Resize if obj == self.live_view.viewport():
                QTimer.singleShot(0, self._keep_live_view_visible)
                return False

            case _:
                return super().eventFilter(obj, event)

    def get_document(self):
        return self.historical_view.document()

    def install_event_filter_on_live_viewport(self, filter_obj):
        self.live_view.viewport().installEventFilter(filter_obj)
