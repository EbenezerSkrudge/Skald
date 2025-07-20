# core/connection.py

import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket

from core.telnet import TelnetParser, TelnetCmd
from collections import deque

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
            on_ga=self._on_ga,
            on_gmcp=self._handle_gmcp
        )

        self._send_queue: deque[tuple[bytes, bool]] = deque()
        self._waiting_for_ga = False
        self._ga_timer = QTimer(self)
        self._ga_timer.setSingleShot(True)
        self._ga_timer.timeout.connect(self._on_ga_timeout)

    def connect_to_host(self, host: str, port: int, timeout: int = 5000):
        self.socket.connectToHost(host, port)
        if not self.socket.waitForConnected(timeout):
            self.errorOccurred.emit(f"[Connection failed] {self.socket.errorString()}")

    def send(self, text: str):
        if self.socket.state() != QTcpSocket.ConnectedState:
            self.errorOccurred.emit("[Error] Not connected.")
            return
        self._send_queue.append(((text + "\n").encode("utf-8"), False))

        if not self._waiting_for_ga:
            self._try_send_next()

    def send_gmcp(self, package: str, payload: Optional[str] = None):
        body = f"{package} {payload}" if payload else package
        msg = bytes([TelnetCmd.IAC, TelnetCmd.SB, TelnetCmd.ATCP2]) + \
              body.encode("utf-8") + \
              bytes([TelnetCmd.IAC, TelnetCmd.SE])
        self._send_queue.append((msg, True))
        log.info(f"[GMCP QUEUED] {body}")

        if not self._waiting_for_ga:
            self._try_send_next()

    def _try_send_next(self):
        if self._waiting_for_ga:
            log.info("[QUEUE] Waiting for GA")
            return

        if not self._send_queue:
            log.info("[QUEUE] Nothing to send")
            return

        msg, wait_for_ga = self._send_queue.popleft()
        log.info(f"[QUEUE] Sending: {msg}")
        self.socket.write(msg)
        self._waiting_for_ga = wait_for_ga

        if wait_for_ga:
            self._ga_timer.start(1000)  # Timeout in milliseconds
        else:
            QTimer.singleShot(0, self._reset_and_send_next)

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

    @Slot()
    def _on_ga(self):
        self._ga_timer.stop()
        self._reset_and_send_next()

    @Slot()
    def _on_ga_timeout(self):
        log.warning("[GA TIMEOUT] Proceeding with next message in queue")
        self._reset_and_send_next()

    def _reset_and_send_next(self):
        self._waiting_for_ga = False
        self._try_send_next()

    # ─── Telnet Parser Callbacks ────────────────────────────────────────────────

    def _handle_data(self, chunk: bytes):
        self.dataReceived.emit(chunk.decode("utf-8", errors="replace"))

    def _handle_negotiation(self, cmd: TelnetCmd, opt: int):
        self.negotiation.emit(int(cmd), opt)

    def _handle_gmcp(self, package: str, payload: Optional[str]):
        self.gmcpReceived.emit(package, payload)
