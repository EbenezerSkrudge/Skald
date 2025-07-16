# core/connection.py

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket

from core.telnet import TelnetParser, TelnetCmd

log = logging.getLogger(__name__)


class MudConnection(QObject):
    dataReceived   = Signal(str)
    negotiation    = Signal(int, int)
    gmcpReceived   = Signal(str, object)
    errorOccurred  = Signal(str)
    disconnected   = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.socket = QTcpSocket(self)
        self.socket.readyRead.connect(self._on_ready_read)
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.errorOccurred.connect(self._on_error)

        self.parser = TelnetParser(
            on_data=self._handle_data,
            on_neg=self._handle_negotiation,
            on_ga=lambda: None,
            on_gmcp=self._handle_gmcp
        )

    def connect_to_host(self, host: str, port: int, timeout: int = 5000):
        self.socket.connectToHost(host, port)
        if not self.socket.waitForConnected(timeout):
            self.errorOccurred.emit(f"[Connection failed] {self.socket.errorString()}")

    def send(self, text: str):
        if self.socket.state() != QTcpSocket.ConnectedState:
            self.errorOccurred.emit("[Error] Not connected.")
            return
        self.socket.write((text + "\n").encode("utf-8"))

    def send_gmcp(self, package: str, payload: Optional[str] = None):
        body = f"{package} {payload}" if payload else package
        msg = bytes([TelnetCmd.IAC, TelnetCmd.SB, TelnetCmd.ATCP2]) + \
              body.encode("utf-8") + \
              bytes([TelnetCmd.IAC, TelnetCmd.SE])
        self.socket.write(msg)
        log.info(f"[GMCP SENT] {body}")

    # ─── Qt Slots ────────────────────────────────────────────────────────────────

    @Slot()
    def _on_connected(self):
        self.dataReceived.emit(
            f"[Connected to {self.socket.peerName()}:{self.socket.peerPort()}]"
        )

    @Slot()
    def _on_disconnected(self):
        self.disconnected.emit()
        self.dataReceived.emit("\n\n[Disconnected from server]\n\n")

    @Slot(QAbstractSocket.SocketError)
    def _on_error(self, code):
        if code != QAbstractSocket.RemoteHostClosedError:
            self.errorOccurred.emit(f"[Socket error] {self.socket.errorString()}")

    @Slot()
    def _on_ready_read(self):
        try:
            data = self.socket.readAll().data()
            self.parser.feed(data)
        except Exception as e:
            self.errorOccurred.emit(f"[Parser error] {e}")

    # ─── Telnet Parser Callbacks ────────────────────────────────────────────────

    def _handle_data(self, chunk: bytes):
        self.dataReceived.emit(chunk.decode("utf-8", errors="replace"))

    def _handle_negotiation(self, cmd: TelnetCmd, opt: int):
        self.negotiation.emit(int(cmd), opt)

    def _handle_gmcp(self, package: str, payload: Optional[str]):
        self.gmcpReceived.emit(package, payload)
