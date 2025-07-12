# ui/widgets/console.py

import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout
)

from PySide6.QtCore import Signal

from core.config import MAX_COMPLETION_LEXICON_SIZE
from ui.tools.convert import ansi_to_html, expand_html
from ui.widgets.console.input_bar import ConsoleInput
from ui.widgets.console.split_display import SplitConsoleDisplay

class Console(QWidget):
    commandEntered = Signal(str)

    def __init__(self):
        super().__init__()

        # A list of all words that have passed through the console
        self.lexicon = []
        self.lexicon_set = set()

        # A list of previously sent user input
        self.history = []

        # Extended QPlainTextInput widget with specific features for console use
        self.input = ConsoleInput(self)

        # Split screen display
        self.display = SplitConsoleDisplay(self)

        # — layout & styling
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setStyleSheet("background-color: black; color: white;")
        self.layout.addWidget(self.display, stretch=1)
        self.layout.addWidget(self.input, stretch=0)

    # ─── Public API ──────────────────────────────────────────────────────────

    def echo(self, raw_text: str):
        # First expand your custom tags into HTML
        html_frag = expand_html(raw_text)

        # If you still need ANSI elsewhere, do:
        html_frag = ansi_to_html(html_frag + "\n")

        # Finally display it
        self.display.echo_html(html_frag)
        self._update_lexicon(raw_text)

    def echo_html(self, html: str, raw_text: str = None):
        """
        Push pre‐built HTML straight into the display,
        and update the lexicon from the un‐escaped text.
        """
        html = expand_html(html)
        self.display.echo_html(html+"<br>")
        self._update_lexicon(raw_text or html)

    def handle_input(self):
        if not self.input.isMasking():
            text = self.input.toPlainText().strip()
            prompt = ">"
            if not text:
                self.input.reset_completion()
                self.input.reset_history_navigation()
                return

            # 1) Wrap in color tag
            command_echo = f"<color=darkcyan>{prompt} {text}</color>\n"

            # 2) Send it directly
            self.echo_html(command_echo, text)

            self.commandEntered.emit(text)
            if text in self.history:
                self.history.remove(text)
            self.history.append(text)

            self.input.selectAll()
            self.input.reset_completion()
            self.input.reset_history_navigation()
        else:
            text = self.input.getUnmaskedText()
            self.input.clear()
            self.commandEntered.emit(text)

    def _update_lexicon(self, text):
        words = re.findall(r"\b\w+\b", text)
        for w in words:
            if w in self.lexicon_set:
                self.lexicon.remove(w)
                self.lexicon_set.remove(w)
            self.lexicon.insert(0, w)
            self.lexicon_set.add(w)
            if len(self.lexicon) > MAX_COMPLETION_LEXICON_SIZE:
                removed = self.lexicon.pop()
                self.lexicon_set.remove(removed)

    # ─── Overrides ──────────────────────────────────────────────────

    def focusNextPrevChild(self, next_widget: bool) -> bool:
        # Prevent Tab and Shift+Tab from changing focus
        return False