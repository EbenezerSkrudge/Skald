# core/widgets/code_editor.py

from PySide6.QtCore import Qt, QRect, QSize, QRegularExpression
from PySide6.QtGui import QFontDatabase, QFont, QColor, QPainter, QTextFormat, QSyntaxHighlighter, QTextCharFormat, \
    QTextCursor
from PySide6.QtWidgets import QWidget, QPlainTextEdit, QVBoxLayout, QTextEdit


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor_widget = editor

    def sizeHint(self):
        return QSize(self.editor_widget.line_number_width(), 0)

    def paintEvent(self, event):
        self.editor_widget.paint_line_numbers(event)


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        # ── String & f-string formats ─────────────────────────
        self.str_format = QTextCharFormat()
        self.str_format.setForeground(QColor("#44CC44"))

        self.fstring_format = QTextCharFormat()
        self.fstring_format.setForeground(QColor("#44CC44"))

        self.fexpr_format = QTextCharFormat()
        self.fexpr_format.setForeground(QColor("#44FFFF"))

        # ── Regex for normal strings and f-strings ────────────
        self.string_patterns = [
            QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            QRegularExpression(r"'''[^']*'''"),
            QRegularExpression(r'"""[^"]*"""')
        ]
        self.fstring_pattern = QRegularExpression(r'''(?<!\w)[fF](['"])(.*?)(\1)''')
        self.fexpr_pattern = QRegularExpression(r"{[^{}]+}")

        # ── Syntax rules (keywords, builtins, constants, ints, decorators, comments) ──
        self.rules = []

        # Keywords (blue + bold)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#4444CC"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif", "else",
            "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
            "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"
        ]
        for keyword in keywords:
            self.rules.append((QRegularExpression(rf"\b{keyword}\b"), keyword_format))

        # Built-in functions (same blue + bold)
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#4444CC"))
        builtin_format.setFontWeight(QFont.Bold)
        builtins = [
            "abs", "all", "any", "bin", "bool", "bytes", "chr", "complex", "dict", "dir", "divmod",
            "enumerate", "eval", "filter", "float", "format", "getattr", "hasattr", "hash", "hex", "id",
            "input", "int", "isinstance", "issubclass", "iter", "len", "list", "map", "max", "min", "next",
            "object", "oct", "open", "ord", "pow", "print", "range", "repr", "reversed", "round", "set",
            "slice", "sorted", "str", "sum", "tuple", "type", "vars", "zip"
        ]
        for builtin_function in builtins:
            self.rules.append((QRegularExpression(rf"\b{builtin_function}\b"), builtin_format))

        # Constants (italic purple)
        constant_format = QTextCharFormat()
        constant_format.setForeground(QColor("#CC44CC"))
        constant_format.setFontItalic(True)
        for c in ("True", "False", "None"):
            self.rules.append((QRegularExpression(rf"\b{c}\b"), constant_format))

        # Integers (purple)
        int_format = QTextCharFormat()
        int_format.setForeground(QColor("#CC44CC"))
        int_pattern = QRegularExpression(r"\b[-+]?(0[xX][\da-fA-F]+|0[bB][01]+|\d+)\b")
        self.rules.append((int_pattern, int_format))

        # Decorators (italic pink-ish)
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#EE44CC"))
        decorator_format.setFontItalic(True)
        decorator_pattern = QRegularExpression(r"@\w+(\.\w+)*")
        self.rules.append((decorator_pattern, decorator_format))

        # Comments (gray italic)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#888888"))
        comment_format.setFontItalic(True)
        comment_pattern = QRegularExpression(r"#.*")
        self.rules.append((comment_pattern, comment_format))

    def highlightBlock(self, text):
        # ── Pass 1: normal strings ─────────────────────────────
        string_ranges = []
        for regex_pattern in self.string_patterns:
            match_iterator = regex_pattern.globalMatch(text)
            while match_iterator.hasNext():
                matched_text = match_iterator.next()
                match_start_index, match_length = matched_text.capturedStart(), matched_text.capturedLength()
                self.setFormat(match_start_index, match_length, self.str_format)
                string_ranges.append((match_start_index, match_start_index + match_length))

        def in_string(position):
            return any(start_position <= position < end_position for start_position, end_position in string_ranges)

        # ── Pass 2: f-string containers ───────────────────────
        fstring_ranges = []
        fstring_matches = self.fstring_pattern.globalMatch(text)
        while fstring_matches.hasNext():
            matched_text = fstring_matches.next()
            match_start_index, match_length = matched_text.capturedStart(), matched_text.capturedLength()
            self.setFormat(match_start_index, match_length, self.fstring_format)
            fstring_ranges.append((match_start_index, match_start_index + match_length))

        # ── Pass 3: other rules outside normal strings ────────
        for regex_pattern, formatting_style in self.rules:
            match_iterator = regex_pattern.globalMatch(text)
            while match_iterator.hasNext():
                matched_text = match_iterator.next()
                match_start_index, match_length = matched_text.capturedStart(), matched_text.capturedLength()
                if not in_string(match_start_index):
                    self.setFormat(match_start_index, match_length, formatting_style)

        # ── Pass 4: override {…} in f-strings ─────────────────
        for f_start, f_end in fstring_ranges:
            segment = text[f_start:f_end]
            inner = self.fexpr_pattern.globalMatch(segment)
            while inner.hasNext():
                matched_text = inner.next()
                match_start_index = f_start + matched_text.capturedStart()
                match_length = matched_text.capturedLength()
                self.setFormat(match_start_index, match_length, self.fexpr_format)

        # ── Pass 5: unmatched brackets & quotes ───────────────
        error_format = QTextCharFormat()
        error_format.setForeground(QColor("#FF3333"))
        error_format.setFontUnderline(True)
        stack = []
        pairs = {"(": ")", "[": "]", "{": "}"}
        quote_state = {"'": False, '"': False}

        for i, current_token in enumerate(text):
            if current_token in quote_state:
                if current_token == "'" and i > 0 and text[i - 1].isalnum():
                    continue
                quote_state[current_token] = not quote_state[current_token]
            elif current_token in pairs:
                stack.append((current_token, i))
            elif current_token in pairs.values():
                if stack and pairs[stack[-1][0]] == current_token:
                    stack.pop()
                else:
                    self.setFormat(i, 1, error_format)

        for _, idx in stack:
            self.setFormat(idx, 1, error_format)

        for q, open_ in quote_state.items():
            if open_:
                idx = text.rfind(q)
                if idx != -1:
                    self.setFormat(idx, 1, error_format)


class CodeTextEdit(QPlainTextEdit):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfBlock)
            block_text = cursor.block().text()

            # 1. Get current indentation
            indent = ""
            for current_char in block_text:
                if current_char in " \t":
                    indent += current_char
                else:
                    break

            # 2. Add extra indent if line ends with ':'
            extra_indent = "    " if block_text.rstrip().endswith(":") else ""

            # 3. Dedent if line starts with a dedent keyword
            dedent_keywords = {"return", "break", "continue", "pass", "raise", "elif", "else", "except", "finally"}
            should_dedent = block_text.lstrip().split(" ")[0] in dedent_keywords

            # Apply indentation
            super().keyPressEvent(event)
            if should_dedent and len(indent) >= 4:
                indent = indent[4:]
            self.insertPlainText(indent + extra_indent)
        else:
            super().keyPressEvent(event)


class CodeEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor = CodeTextEdit()
        font_db = QFontDatabase()
        mono_family = font_db.systemFont(QFontDatabase.FixedFont).family()
        mono_font = QFont(mono_family, 11)

        self.editor.setFont(mono_font)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setTabStopDistance(4 * self.editor.fontMetrics().horizontalAdvance(' '))
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0c0c0c;  /* dark gray background */
                color: #dcdcdc;             /* light gray text */
                selection-background-color: #44475a;
            }
        """)

        layout.addWidget(self.editor)

        # Add line number area
        self.line_area = LineNumberArea(self)
        self.editor.blockCountChanged.connect(self.update_line_number_area_width)
        self.editor.updateRequest.connect(self.update_line_number_area)
        self.editor.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        self.highlighter = PythonHighlighter(self.editor.document())

    def line_number_width(self):
        digits = len(str(max(1, self.editor.blockCount())))
        space = 10 + self.editor.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.editor.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_area.scroll(0, dy)
        else:
            self.line_area.update(0, rect.y(), self.line_area.width(), rect.height())
        if rect.contains(self.editor.viewport().rect()):
            self.update_line_number_area_width(0)

    def highlight_current_line(self):
        extra = QTextEdit.ExtraSelection()
        line_color = QColor("#1e1e1e")
        extra.format.setBackground(line_color)
        extra.format.setProperty(QTextFormat.FullWidthSelection, True)
        extra.cursor = self.editor.textCursor()
        extra.cursor.clearSelection()
        self.editor.setExtraSelections([extra])

    def paint_line_numbers(self, event):
        painter = QPainter(self.line_area)
        painter.fillRect(event.rect(), QColor("#2b2b2b"))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.editor.blockBoundingGeometry(block).translated(
            self.editor.contentOffset()).top())
        bottom = top + int(self.editor.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#d0d0d0"))
                painter.drawText(0, top, self.line_area.width() - 4,
                                 self.editor.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.editor.blockBoundingRect(block).height())
            block_number += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        content_rect = self.editor.contentsRect()
        self.line_area.setGeometry(
            QRect(content_rect.left(), content_rect.top(), self.line_number_width(), content_rect.height()))

    def set_text(self, text: str):
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()

    def sizeHint(self):
        return self.editor.sizeHint()

    def clear(self):
        """
        Clear the text in the embedded editor.
        This makes CodeEditor.clear() valid for calling code.
        """
        self.editor.clear()
