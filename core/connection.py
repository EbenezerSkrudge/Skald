# core/connection.py

import logging
from typing      import Optional
from PySide6.QtCore import QObject, Signal, Slot, QByteArray
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket

from core.telnet import TelnetParser, TelnetCmd

logging.basicConfig(
    level=logging.DEBUG,  # or INFO, WARNING, etc.
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

log = logging.getLogger(__name__)

class MudConnection(QObject):
    dataReceived  = Signal(str)
    negotiation   = Signal(int, int)
    gmcpReceived  = Signal(str, object)
    errorOccurred = Signal(str)
    disconnected  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.socket = QTcpSocket(self)
        self.socket.readyRead.connect(self._on_ready_read)
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.errorOccurred.connect(self._on_error)

        self.parser = TelnetParser(
          on_data = self._parser_data,
          on_neg  = self._parser_neg,
          on_ga   = lambda: None,
          on_gmcp = self._parser_gmcp
        )

    def connect_to_host(self, host: str, port: int, timeout=5000):
        self.socket.connectToHost(host, port)
        if not self.socket.waitForConnected(timeout):
            self.errorOccurred.emit(f"[Connection failed] {self.socket.errorString()}")

    @Slot()
    def _on_connected(self):
        self.dataReceived.emit(f"[Connected to {self.socket.peerName()}:{self.socket.peerPort()}]")

    @Slot()
    def _on_disconnected(self):
        self.disconnected.emit()
        self.dataReceived.emit("\n\n[Disconnected from server]\n\n")

    @Slot(QAbstractSocket.SocketError)
    def _on_error(self, code):
        # Ignore the “remote host closed” code—let disconnected() handle it
        if code == QAbstractSocket.RemoteHostClosedError:
            return

        # All other errors still get reported
        msg = self.socket.errorString()
        self.errorOccurred.emit(f"[Socket error] {msg}")

    @Slot()
    def _on_ready_read(self):
        # readAll() returns a QByteArray, whose .data() is a Python bytes
        ba: QByteArray = self.socket.readAll()
        buf: bytes = ba.data()
        try:
            self.parser.feed(buf)
        except Exception as e:
            self.errorOccurred.emit(f"[Parser error] {e}")

    def send(self, text: str):
        if self.socket.state() != QTcpSocket.ConnectedState:
            self.errorOccurred.emit("[Error] Not connected.")
            return
        self.socket.write(text.encode("utf-8") + b"\n")

    def send_gmcp(self, package: str, payload: Optional[str] = None):
        body = package if payload is None else f"{package} {payload}"
        msg = bytes([TelnetCmd.IAC, TelnetCmd.SB, TelnetCmd.ATCP2]) \
              + body.encode("utf-8") \
              + bytes([TelnetCmd.IAC, TelnetCmd.SE])
        self.socket.write(msg)
        logging.info(f"[GMCP SENT] {msg}")

    # ─ Parser callbacks ─────────────────────────────────

    def _parser_data(self, chunk: bytes):
        text = chunk.decode("utf-8", errors="replace")
        self.dataReceived.emit(text)

    def _parser_neg(self, cmd: TelnetCmd, opt: int):
        self.negotiation.emit(int(cmd), opt)

    def _parser_gmcp(self, package: str, payload: Optional[str]):
        self.gmcpReceived.emit(package, payload)
