# core/telnet.py

import logging
from enum import IntEnum
from typing import Callable, Optional, Union, List, Tuple, Literal

log = logging.getLogger(__name__)

class TelnetCmd(IntEnum):
    IAC   = 255
    DONT  = 254
    DO    = 253
    WONT  = 252
    WILL  = 251
    SB    = 250
    GA    = 249
    SE    = 240
    ATCP2 = 201
    ECHO  = 1

# Frame types
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
    MAX_SB_LEN = 4096

    def __init__(
        self,
        *,
        on_data: Optional[Callable[[bytes], None]] = None,
        on_neg: Optional[Callable[[TelnetCmd, int], None]] = None,
        on_ga: Optional[Callable[[], None]] = None,
        on_gmcp: Optional[Callable[[str, Optional[str]], None]] = None,
        on_sb: Optional[Callable[[int, bytes], None]] = None,
    ):
        self.on_data = on_data
        self.on_neg = on_neg
        self.on_ga = on_ga
        self.on_gmcp = on_gmcp
        self.on_sb = on_sb

        self.state = 'data'
        self._pend_cmd: Optional[TelnetCmd] = None
        self.sb_opt: Optional[int] = None
        self.sb_buf = bytearray()

    def feed(self, chunk: bytes) -> List[TelnetFrame]:
        out: List[TelnetFrame] = []

        for byte in chunk:
            if self.state == 'data':
                if byte == TelnetCmd.IAC:
                    self.state = 'iac'
                elif byte != 0:
                    out.append(('data', bytes([byte])))

            elif self.state == 'iac':
                if byte == TelnetCmd.IAC:
                    out.append(('data', b'\xff'))
                    self.state = 'data'
                elif byte == TelnetCmd.GA:
                    out.append(('ga', None))
                    self.state = 'data'
                elif byte == TelnetCmd.SB:
                    self.state = 'sb_opt'
                elif byte in (TelnetCmd.WILL, TelnetCmd.WONT, TelnetCmd.DO, TelnetCmd.DONT):
                    self._pend_cmd = TelnetCmd(byte)
                    self.state = 'iac_cmd_option'
                else:
                    log.debug("[TELNET] Unknown IAC command: %r", byte)
                    self.state = 'data'

            elif self.state == 'iac_cmd_option':
                out.append(('neg', self._pend_cmd, byte))
                self._pend_cmd = None
                self.state = 'data'

            elif self.state == 'sb_opt':
                self.sb_opt = byte
                self.sb_buf.clear()
                self.state = 'sb_data'

            elif self.state == 'sb_data':
                if byte == TelnetCmd.IAC:
                    self.state = 'sb_data_iac'
                else:
                    self.sb_buf.append(byte)
                    if len(self.sb_buf) > self.MAX_SB_LEN:
                        log.warning("[TELNET] SB payload too large; discarding")
                        self.sb_buf.clear()
                        self.state = 'data'

            elif self.state == 'sb_data_iac':
                if byte == TelnetCmd.SE:
                    out.append(('sb', self.sb_opt, bytes(self.sb_buf)))
                    self.state = 'data'
                elif byte == TelnetCmd.IAC:
                    self.sb_buf.append(TelnetCmd.IAC)
                    self.state = 'sb_data'
                else:
                    self.sb_buf.clear()
                    self.state = 'data'

        return self._process_frames(out)

    def _process_frames(self, frames: List[TelnetFrame]) -> List[TelnetFrame]:
        merged: List[TelnetFrame] = []
        buffer = bytearray()

        # Merge consecutive data frames
        for frame in frames:
            if frame[0] == 'data':
                buffer.extend(frame[1])  # type: ignore
            else:
                if buffer:
                    merged.append(('data', bytes(buffer)))
                    buffer.clear()
                merged.append(frame)
        if buffer:
            merged.append(('data', bytes(buffer)))

        final: List[TelnetFrame] = []
        for frame in merged:
            match frame:
                case ('data', data):
                    cleaned = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                    final.append(('data', cleaned))
                    if self.on_data:
                        self.on_data(cleaned)

                case ('neg', cmd, opt):
                    final.append(frame)
                    if self.on_neg:
                        self.on_neg(cmd, opt)
                    log.info(f"[NEG] {cmd.name} {opt}")

                case ('ga', _):
                    final.append(frame)
                    if self.on_ga:
                        self.on_ga()
                    log.info("[GA]")

                case ('sb', opt, payload):
                    final.append(frame)
                    if opt == TelnetCmd.ATCP2:
                        try:
                            text = payload.decode('utf-8')
                            package, _, raw_payload = text.partition(' ')
                            if self.on_gmcp:
                                self.on_gmcp(package, raw_payload or None)
                        except Exception as e:
                            log.warning("[TELNET] GMCP decode failed: %s", e)
                    elif self.on_sb:
                        self.on_sb(opt, payload)

                case _:
                    log.warning("[TELNET] Unrecognized frame: %r", frame)

        return final
