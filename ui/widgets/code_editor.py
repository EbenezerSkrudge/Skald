# core/widgets/code_editor.py

from PySide6.QtWidgets import QWidget, QPlainTextEdit, QVBoxLayout
from PySide6.QtGui     import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
from PySide6.QtCore    import QRegularExpression

class PythonHighlighter(QSyntaxHighlighter):
    """
    Simple syntax highlighter for a handful of Python keywords.
    """
    def __init__(self, document):
        super().__init__(document)
        # format for keywords
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#00008B"))  # dark blue
        kw_format.setFontWeight(QFont.Bold)

        keywords = [
            "def", "class", "if", "elif", "else", "for", "while",
            "import", "from", "return", "with", "as", "try", "except",
            "finally", "raise", "assert", "lambda"
        ]

        # build a list of (regex, format) tuples
        self.rules = [
            (QRegularExpression(rf"\b{kw}\b"), kw_format)
            for kw in keywords
        ]

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, fmt)


class CodeEditor(QWidget):
    """
    A minimal code‐editing widget with Python syntax highlighting.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor = QPlainTextEdit()
        # disable word‐wrap and use a monospaced font
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setFont(QFont("Consolas", 11))

        # attach the highlighter to the document
        self.highlighter = PythonHighlighter(self.editor.document())

        layout.addWidget(self.editor)

    def setText(self, text: str):
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()