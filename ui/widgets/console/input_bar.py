# ui/widgets/console/input_bar.py

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, QTimer, QPoint

from ui.style import get_mono_font
from core.config import COMPLETION_POPUP_MAX_ROWS


class ConsoleInput(QPlainTextEdit):
    def __init__(self, console):
        super().__init__()

        self.console = console

        self._input_min_lines = 1
        self._input_max_lines = 10

        self.setFont(get_mono_font())
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        line_height = self.fontMetrics().height()
        doc_margin = self.document().documentMargin()
        frame_margin = self.frameWidth()
        total_height = line_height + (2 * doc_margin) + (2 * frame_margin)
        self.setFixedHeight(int(total_height))

        self.textChanged.connect(lambda: QTimer.singleShot(0, self._update_input_height))

        # History
        self.history = console.history
        self.history_prefix = ""
        self.history_index = -1
        self.history_matches = []
        self.history_mode_all = False

        # Autocomplete
        self.completion_prefix = ""
        self.completion_index = -1
        self.completion_matches = []
        self.prefix_start_pos = -1

        # Completion popup
        self.completion_popup = QListWidget(self)
        self.completion_popup.setWindowFlags(Qt.ToolTip)
        self.completion_popup.setFocusPolicy(Qt.NoFocus)
        self.completion_popup.setMouseTracking(False)
        self.completion_popup.setFont(get_mono_font())

        # Input masking
        self._masking = False
        self._buffer = ""       # Stores masked text

    def _update_input_height(self):
        doc = self.document()
        doc.adjustSize()
        metrics = self.fontMetrics()
        line_height = metrics.lineSpacing()
        doc_margin = doc.documentMargin()
        frame_width = self.frameWidth()

        block = doc.begin()
        total_lines = 0
        while block.isValid():
            layout = block.layout()
            if layout:
                total_lines += layout.lineCount()
            block = block.next()

        lines = max(self._input_min_lines, min(self._input_max_lines, total_lines))
        final_height = int(lines * line_height + 3 * (doc_margin + frame_width))

        self.setUpdatesEnabled(False)
        self.setMinimumHeight(final_height)
        self.setMaximumHeight(final_height)
        self.setUpdatesEnabled(True)

        def _scroll():
            if total_lines < self._input_max_lines:
                self.verticalScrollBar().setValue(0)
            else:
                cursor_rect = self.cursorRect()
                view_rect = self.viewport().rect()
                if cursor_rect.bottom() > view_rect.bottom():
                    self.ensureCursorVisible()

        if total_lines >= self._input_max_lines:
            QTimer.singleShot(0, _scroll)
        else:
            self.verticalScrollBar().setValue(0)

    # ─── Tab Completion ─────────────────────────────────────────────

    def reset_completion(self):
        self.completion_prefix = ""
        self.prefix_start_pos = -1
        self.completion_index = -1
        self.completion_matches.clear()
        self.completion_popup.hide()
        self.completion_popup.clear()

    def reset_history_navigation(self):
        self.history_prefix = ""
        self.history_mode_all = False
        self.history_index = -1
        self.history_matches.clear()

    def handle_completion(self, direction=1):
        if self._masking:
            return False

        cursor_obj = self.textCursor()
        cursor_pos = cursor_obj.position()
        text = self.toPlainText()

        if self.completion_prefix and self.completion_matches:
            self.completion_index = (self.completion_index + direction) % len(self.completion_matches)
        else:
            before = text[:cursor_pos]
            parts = before.rsplit(" ", 1)
            self.completion_prefix = parts[-1] if parts else ""
            self.prefix_start_pos = cursor_pos - len(self.completion_prefix)
            self.completion_matches = [
                w for w in self.console.lexicon
                if w.lower().startswith(self.completion_prefix.lower())
            ]
            self.completion_index = 0

        if not self.completion_matches:
            self.reset_completion()
            self.reset_history_navigation()
            return True

        choice = self.completion_matches[self.completion_index]
        new_text = text[:self.prefix_start_pos] + choice + text[cursor_pos:]

        self.setPlainText(new_text)
        new_cursor = self.textCursor()
        new_cursor.setPosition(self.prefix_start_pos + len(choice))
        self.setTextCursor(new_cursor)

        self.show_completion_popup()
        return True

    def show_completion_popup(self):
        self.completion_popup.clear()
        for i, s in enumerate(self.completion_matches):
            item = QListWidgetItem(s)
            if i == self.completion_index:
                item.setSelected(True)
            self.completion_popup.addItem(item)
        self.completion_popup.setCurrentRow(self.completion_index)

        row_h = self.completion_popup.sizeHintForRow(0)
        rows = min(len(self.completion_matches), COMPLETION_POPUP_MAX_ROWS)
        pos = self.mapToGlobal(QPoint(0, -row_h * rows))
        self.completion_popup.move(pos)
        self.completion_popup.resize(self.width(), row_h * rows)
        self.completion_popup.show()

    def _restore_completion_prefix(self):
        p = self.prefix_start_pos
        full = self.toPlainText()
        cp = self.textCursor().position()
        rebuilt = full[:p] + self.completion_prefix + full[cp:]
        self.blockSignals(True)
        self.setPlainText(rebuilt)
        cur = self.textCursor()
        cur.setPosition(p + len(self.completion_prefix))
        self.setTextCursor(cur)
        self.blockSignals(False)
        self.reset_completion()
        self.reset_history_navigation()

    # ─── Command History ─────────────────────────────────────────────

    def search_history(self, direction: int) -> bool:
        if not self.history:
            return False

        if self._masking:
            return False

        cursor = self.textCursor()
        raw_text = self.toPlainText()
        # If the user has selected the entire line, we’ll match all history
        # but remember the original text so we can skip it on first match
        is_full_select = cursor.hasSelection()
        prefix = "" if is_full_select else raw_text

        # Build matches on first invocation
        if self.history_index == -1:
            self.history_matches = [
                cmd for cmd in self.history
                if cmd.lower().startswith(prefix.lower())
            ]
            if not self.history_matches:
                return False

            # Start at the newest match for Up (direction==1)
            if direction == 1:
                idx = len(self.history_matches) - 1

                # If this exactly equals the selected text, bump back one more
                if is_full_select and idx >= 0 and \
                        self.history_matches[idx].lower() == raw_text.lower():
                    idx = max(0, idx - 1)

                self.history_index = idx
            else:
                return False

        else:
            # Already navigating history
            if direction == 1:  # Up => older entries
                if self.history_index > 0:
                    self.history_index -= 1
            else:  # Down => newer entries
                if self.history_index < len(self.history_matches) - 1:
                    self.history_index += 1
                else:
                    # Back to live input
                    self.history_index = -1
                    self.clear()
                    self.reset_completion()
                    return True

        # Display the selected entry
        entry = self.history_matches[self.history_index]
        self.blockSignals(True)
        self.setPlainText(entry)
        cur = self.textCursor()
        cur.movePosition(QTextCursor.End)
        self.setTextCursor(cur)
        self.blockSignals(False)

        self.reset_completion()
        return True

    def _restore_history_prefix(self):
        prefix = self.history_prefix or ""
        self.blockSignals(True)
        self.setPlainText(prefix)
        cur = self.textCursor()
        cur.setPosition(len(prefix))
        self.setTextCursor(cur)
        self.blockSignals(False)
        self.reset_completion()
        self.reset_history_navigation()

    def setMasking(self, enabled: bool):
        """Turn password-masking on or off."""
        self._masking = enabled
        # if switching modes, rewrite what's shown
        display = "●" * len(self._buffer) if enabled else self._buffer
        self.blockSignals(True)
        self.setPlainText(display)
        # move cursor to end
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.blockSignals(False)

    # ─── Masked input methods ───────────────────────────────────

    def isMasking(self) -> bool:
        return self._masking

    def getUnmaskedText(self) -> str:
        """Return the real, unmasked text."""
        return self._buffer

    def _refresh_masked_display(self):
        masked = "●" * len(self._buffer)
        self.blockSignals(True)
        self.setPlainText(masked)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.blockSignals(False)

    def clear(self):
        """
        Modify built in clear to also clear the masked text buffer
        :return:
        """
        self._buffer = ""
        super().clear()

    # ─── Event Hooks ─────────────────────────────────────────────

    def keyPressEvent(self, event):
        key  = event.key()
        mods = event.modifiers()
        text = event.text()

        # ─── Masked (password) mode ──────────────────────────
        if self._masking:
            match key:
                # submit on Enter (unless Shift+Enter)
                case Qt.Key_Return | Qt.Key_Enter if not (mods & Qt.ShiftModifier):
                    self.console.handle_input()
                    return

                # allow Shift+Enter to insert a newline
                case Qt.Key_Return | Qt.Key_Enter:
                    return super().keyPressEvent(event)

                # backspace: pop buffer
                case Qt.Key_Backspace:
                    self._buffer = self._buffer[:-1]
                    self._refresh_masked_display()
                    return

                # any printable character
                case _ if text:
                    self._buffer += text
                    super().insertPlainText("●")
                    return

                # everything else falls back
                case _:
                    return super().keyPressEvent(event)

        # ─── Normal mode ──────────────────────────────────────
        match key:
            # pure modifiers: let Qt handle them
            case Qt.Key_Shift | Qt.Key_Control | Qt.Key_Alt | Qt.Key_Meta:
                return super().keyPressEvent(event)

            # submit on Enter (unless Shift+Enter)
            case Qt.Key_Return | Qt.Key_Enter if not (mods & Qt.ShiftModifier):
                self.console.handle_input()
                return

            # allow Shift+Enter to insert a newline
            case Qt.Key_Return | Qt.Key_Enter:
                return super().keyPressEvent(event)

            # tab-complete
            case Qt.Key_Tab if self.handle_completion(1):
                return
            case Qt.Key_Tab:
                return super().keyPressEvent(event)

            case Qt.Key_Backtab if self.handle_completion(-1):
                return
            case Qt.Key_Backtab:
                return super().keyPressEvent(event)

            # history navigation
            case Qt.Key_Up if self.search_history(1):
                return
            case Qt.Key_Up:
                return super().keyPressEvent(event)

            case Qt.Key_Down if self.search_history(-1):
                return
            case Qt.Key_Down:
                return super().keyPressEvent(event)

            # space-clears completion popup
            case Qt.Key_Space if self.completion_index >= 0:
                self.reset_completion()
                self.reset_history_navigation()
                return super().keyPressEvent(event)

            # smart backspace for history/completion
            case Qt.Key_Backspace if self.history_index != -1:
                self._restore_history_prefix()
                return
            case Qt.Key_Backspace if self.completion_prefix and self.prefix_start_pos >= 0:
                self._restore_completion_prefix()
                return
            case Qt.Key_Backspace:
                return super().keyPressEvent(event)

            # escape: clear popups
            case Qt.Key_Escape:
                self.reset_completion()
                self.reset_history_navigation()
                return

            # all other keys
            case _:
                self.reset_completion()
                self.reset_history_navigation()
                return super().keyPressEvent(event)
