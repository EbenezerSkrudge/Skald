# core/widgets/code_editor.py

from PySide6.QtWidgets import QWidget, QPlainTextEdit, QVBoxLayout, QTextEdit
from PySide6.QtGui import QFontDatabase, QFont, QColor, QPainter, QTextFormat, QSyntaxHighlighter, QTextCharFormat, \
    QTextCursor
from PySide6.QtCore import Qt, QRect, QSize, QRegularExpression


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor_widget= editor

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
        self.fexpr_pattern   = QRegularExpression(r"{[^{}]+}")

        # ── Syntax rules (keywords, builtins, constants, ints, decorators, comments) ──
        self.rules = []

        # Keywords (blue + bold)
        kw_fmt = QTextCharFormat(); kw_fmt.setForeground(QColor("#4444CC")); kw_fmt.setFontWeight(QFont.Bold)
        keywords = [
            "and","as","assert","async","await","break","class","continue","def","del","elif","else",
            "except","finally","for","from","global","if","import","in","is","lambda","nonlocal",
            "not","or","pass","raise","return","try","while","with","yield"
        ]
        for kw in keywords:
            self.rules.append((QRegularExpression(rf"\b{kw}\b"), kw_fmt))

        # Built-in functions (same blue + bold)
        bi_fmt = QTextCharFormat(); bi_fmt.setForeground(QColor("#4444CC")); bi_fmt.setFontWeight(QFont.Bold)
        builtins = [
            "abs","all","any","bin","bool","bytes","chr","complex","dict","dir","divmod",
            "enumerate","eval","filter","float","format","getattr","hasattr","hash","hex","id",
            "input","int","isinstance","issubclass","iter","len","list","map","max","min","next",
            "object","oct","open","ord","pow","print","range","repr","reversed","round","set",
            "slice","sorted","str","sum","tuple","type","vars","zip"
        ]
        for fn in builtins:
            self.rules.append((QRegularExpression(rf"\b{fn}\b"), bi_fmt))

        # Constants (italic purple)
        const_fmt = QTextCharFormat(); const_fmt.setForeground(QColor("#CC44CC")); const_fmt.setFontItalic(True)
        for c in ("True","False","None"):
            self.rules.append((QRegularExpression(rf"\b{c}\b"), const_fmt))

        # Integers (purple)
        int_fmt = QTextCharFormat(); int_fmt.setForeground(QColor("#CC44CC"))
        int_pat = QRegularExpression(r"\b[-+]?(0[xX][\da-fA-F]+|0[bB][01]+|\d+)\b")
        self.rules.append((int_pat, int_fmt))

        # Decorators (italic pink-ish)
        dec_fmt = QTextCharFormat(); dec_fmt.setForeground(QColor("#EE44CC")); dec_fmt.setFontItalic(True)
        dec_pat = QRegularExpression(r"@\w+(\.\w+)*")
        self.rules.append((dec_pat, dec_fmt))

        # Comments (gray italic)
        com_fmt = QTextCharFormat(); com_fmt.setForeground(QColor("#888888")); com_fmt.setFontItalic(True)
        com_pat = QRegularExpression(r"#.*")
        self.rules.append((com_pat, com_fmt))

    def highlightBlock(self, text):
        # ── Pass 1: normal strings ─────────────────────────────
        string_ranges = []
        for pat in self.string_patterns:
            it = pat.globalMatch(text)
            while it.hasNext():
                m = it.next()
                s, l = m.capturedStart(), m.capturedLength()
                self.setFormat(s, l, self.str_format)
                string_ranges.append((s, s + l))

        def in_string(pos):
            return any(s <= pos < e for s, e in string_ranges)

        # ── Pass 2: f-string containers ───────────────────────
        fstring_ranges = []
        fit = self.fstring_pattern.globalMatch(text)
        while fit.hasNext():
            m = fit.next()
            s, l = m.capturedStart(), m.capturedLength()
            self.setFormat(s, l, self.fstring_format)
            fstring_ranges.append((s, s + l))

        # ── Pass 3: other rules outside normal strings ────────
        for pat, fmt in self.rules:
            it = pat.globalMatch(text)
            while it.hasNext():
                m = it.next()
                s, l = m.capturedStart(), m.capturedLength()
                if not in_string(s):
                    self.setFormat(s, l, fmt)

        # ── Pass 4: override {…} in f-strings ─────────────────
        for f_start, f_end in fstring_ranges:
            segment = text[f_start:f_end]
            inner = self.fexpr_pattern.globalMatch(segment)
            while inner.hasNext():
                m = inner.next()
                s = f_start + m.capturedStart()
                l = m.capturedLength()
                self.setFormat(s, l, self.fexpr_format)

        # ── Pass 5: unmatched brackets & quotes ───────────────
        err_fmt = QTextCharFormat(); err_fmt.setForeground(QColor("#FF3333")); err_fmt.setFontUnderline(True)
        stack = []
        pairs = {"(":")","[":"]","{":"}"}
        quote_state = {"'": False, '"': False}

        for i, ch in enumerate(text):
            if ch in quote_state:
                if ch == "'" and i>0 and text[i-1].isalnum():
                    continue
                quote_state[ch] = not quote_state[ch]
            elif ch in pairs:
                stack.append((ch, i))
            elif ch in pairs.values():
                if stack and pairs[stack[-1][0]] == ch:
                    stack.pop()
                else:
                    self.setFormat(i, 1, err_fmt)

        for _, idx in stack:
            self.setFormat(idx, 1, err_fmt)

        for q, open_ in quote_state.items():
            if open_:
                idx = text.rfind(q)
                if idx != -1:
                    self.setFormat(idx, 1, err_fmt)


class CodeTextEdit(QPlainTextEdit):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfBlock)
            block_text = cursor.block().text()

            # 1. Get current indentation
            indent = ""
            for ch in block_text:
                if ch in " \t":
                    indent += ch
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

        self.editor = self.editor = CodeTextEdit()
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
        cr = self.editor.contentsRect()
        self.line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def set_text(self, text: str):
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()

    def sizeHint(self):
        return self.editor.sizeHint()
