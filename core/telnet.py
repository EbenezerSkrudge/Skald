# core/telnet.py

import logging
from enum import IntEnum
from typing import (
    List, Tuple, Union, Optional, Callable, Literal
)

log = logging.getLogger(__name__)

class TelnetCmd(IntEnum):
    """
    Telnet command codes, plus the GMCP option (ATCP2).
    """
    IAC   = 255  # "Interpret as Command"
    DONT  = 254
    DO    = 253
    WONT  = 252
    WILL  = 251
    SB    = 250  # Subnegotiation Begin
    GA    = 249  # Go Ahead
    SE    = 240  # Subnegotiation End

    ATCP2 = 201  # GMCP (ATCP2) option
    ECHO = 1

# Frame type aliases
TelnetDataFrame = Tuple[Literal['data'], bytes]
TelnetNegFrame  = Tuple[Literal['neg'], TelnetCmd, int]
TelnetSbFrame   = Tuple[Literal['sb'], int, bytes]
TelnetGaFrame   = Tuple[Literal['ga'], None]
TelnetGmcpFrame = Tuple[Literal['gmcp'], str, Optional[str]]

TelnetFrame = Union[
    TelnetDataFrame,
    TelnetNegFrame,
    TelnetSbFrame,
    TelnetGaFrame,
    TelnetGmcpFrame
]


class TelnetParser:
    """
    Minimal Telnet state machine:
      - emits ('data', b'...')
      - emits ('neg', TelnetCmd.WILL, option)
      - emits ('sb', option, payload_bytes)
      - emits ('ga', None)
    Supports plugin callbacks and normalizes newlines.
    """

    # Maximum subnegotiation payload to prevent runaway
    MAX_SB_LEN = 4096

    def __init__(
        self,
        *,
        on_data: Optional[Callable[[bytes], None]] = None,
        on_neg: Optional[Callable[[TelnetCmd, int], None]] = None,
        on_ga: Optional[Callable[[], None]] = None,
        on_gmcp: Optional[Callable[[str, Optional[str]], None]] = None,
        on_sb: Callable[[int, bytes], None] = None
    ):
        """
            Initialize parser state and plugin hooks.
        """
        # Set hooks
        self.on_data = on_data
        self.on_neg = on_neg
        self.on_ga = on_ga
        self.on_gmcp = on_gmcp
        self.on_sb = on_sb

        self.state: str = 'data'
        self._pend_cmd: Optional[TelnetCmd] = None
        self.sb_opt: Optional[int] = None
        self.sb_buf: bytearray = bytearray()

    def feed(self, chunk: bytes) -> List[TelnetFrame]:
        """
        Consume raw bytes and return Telnet frames.
        Also invokes plugin callbacks for each frame.
        """
        out: List[TelnetFrame] = []

        for byte in chunk:
            match self.state:
                case 'data':
                    match byte:
                        case TelnetCmd.IAC:
                            self.state = 'iac'
                        case 0:
                            continue  # Ignore NUL
                        case _:
                            out.append(('data', bytes([byte])))

                case 'iac':
                    match byte:
                        case TelnetCmd.IAC:
                            out.append(('data', b'\xff'))  # Escaped 255
                            self.state = 'data'
                        case TelnetCmd.GA:
                            out.append(('ga', None))
                            self.state = 'data'
                        case TelnetCmd.SB:
                            self.state = 'sb_opt'
                        case TelnetCmd.WILL | TelnetCmd.WONT | TelnetCmd.DO | TelnetCmd.DONT:
                            self._pend_cmd = TelnetCmd(byte)
                            self.state = 'iac_cmd_option'
                        case _:
                            log.debug("[TELNET] Unrecognized IAC code: %r", byte)
                            self.state = 'data'

                case 'iac_cmd_option':
                    out.append(('neg', self._pend_cmd, byte))
                    self._pend_cmd = None
                    self.state = 'data'

                case 'sb_opt':
                    self.sb_opt = byte
                    self.sb_buf.clear()
                    self.state = 'sb_data'

                case 'sb_data':
                    if byte == TelnetCmd.IAC:
                        self.state = 'sb_data_iac'
                    else:
                        self.sb_buf.append(byte)
                        if len(self.sb_buf) > self.MAX_SB_LEN:
                            log.warning("[TELNET] SB payload too large; discarding")
                            self.sb_buf.clear()
                            self.state = 'data'

                case 'sb_data_iac':
                    match byte:
                        case TelnetCmd.SE:
                            out.append(('sb', self.sb_opt, bytes(self.sb_buf)))
                            self.state = 'data'
                        case TelnetCmd.IAC:
                            self.sb_buf.append(TelnetCmd.IAC)
                            self.state = 'sb_data'
                        case _:
                            self.sb_buf.clear()
                            self.state = 'data'

        # Merge consecutive data frames
        merged: List[TelnetFrame] = []
        buffer = bytearray()
        for frame in out:
            typ = frame[0]
            if typ == 'data':
                buffer.extend(frame[1])  # type: ignore
            else:
                if buffer:
                    merged.append(('data', bytes(buffer)))
                    buffer.clear()
                merged.append(frame)
        if buffer:
            merged.append(('data', bytes(buffer)))

        # Normalize newlines and dispatch callbacks
        final: List[TelnetFrame] = []
        for frame in merged:
            match frame:
                case ('data', data_bytes):
                    cleaned = data_bytes.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                    final.append(('data', cleaned))
                    self.on_data(cleaned)

                case ('neg', TelnetCmd() as cmd, int(opt)):
                    final.append(('neg', cmd, opt))
                    self.on_neg(cmd, opt)

                case ('sb', int(opt), bytes() as payload):
                    final.append(('sb', opt, payload))
                    if opt == TelnetCmd.ATCP2:
                        try:
                            text = payload.decode('utf-8')
                            parts = text.split(' ', 1)
                            msg = parts[0]
                            raw_payload = parts[1] if len(parts) > 1 else None

                            self.on_gmcp(msg, raw_payload)
                        except Exception as e:
                            log.warning("[TELNET] GMCP decode failed: %s", e)

                case ('ga', None):
                    final.append(('ga', None))
                    self.on_ga()

                case _:
                    log.warning("[TELNET] Unrecognized Telnet frame: %r", frame)

        return final

