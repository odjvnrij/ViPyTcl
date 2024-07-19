from enum import IntEnum

from .. import __version__

_big_ver = int(__version__.split(".")[0])
_little_ver = int(__version__.split(".")[1])
_ver_bytes = _big_ver.to_bytes(1, byteorder="big") + _little_ver.to_bytes(1, byteorder="big")


class TclMsgType(IntEnum):
    HeartBeat = 0x0100
    CmdReq = 0x0201
    CmdResp = 0x0202


class CmdRunStat(IntEnum):
    Receive = 0x01
    Run = 0x02
    Done = 0x10
    Fail = 0x11


class TclMsg:
    def __init__(self, msg_type: TclMsgType):
        self.msg_type = msg_type
        self.total_len = 16

    def get_header(self):
        return (
                b"\x54\x54\x54\x54" +
                int.to_bytes(self.total_len, 4, "big") +
                int.to_bytes(self.msg_type, 2, "big") + _ver_bytes +
                b"\x00\x00\x00\x00"
        )


class HeartBeatMsg(TclMsg):
    def __init__(self):
        super().__init__(TclMsgType.HeartBeat)


class CmdReqMsg(TclMsg):
    def __init__(self, addr: tuple, cmd: str, stat: int = CmdRunStat.Receive, timeout: int = 0):
        super().__init__(TclMsgType.CmdReq)
        self.cmd = cmd.encode()
        self.cmd_len = len(cmd)
        self.total_len += 4 + self.cmd_len
        self.addr = addr
        self.stat = stat
        self.timeout = timeout

    def get_bytes(self):
        return (self.get_header() +
                int.to_bytes(self.timeout, 3, "big") +
                int.to_bytes(self.stat, 1, "big") +
                self.cmd
                )


class CmdRespMsg(TclMsg):
    def __init__(self, addr: tuple, cmd: str, stat: int = CmdRunStat.Done, result: str = "", timeout: int = 0):
        super().__init__(TclMsgType.CmdResp)
        self.addr = addr
        self.stat = stat
        self.cmd = cmd.encode()
        self.cmd_len = len(cmd)
        self.result = result.encode()
        self.result_len = len(result)
        self.timeout = timeout
        self.total_len += 4 + self.result_len

    def get_bytes(self):
        return (self.get_header() +
                int.to_bytes(self.timeout, 3, "big") +
                int.to_bytes(self.stat, 1, "big") +
                self.result
                )

    @classmethod
    def from_req(cls, req_msg: CmdReqMsg, result: str):
        obj = cls(req_msg.addr, "", CmdRunStat.Done, "")
        obj.cmd = req_msg.cmd
        obj.cmd_len = req_msg.cmd_len
        obj.result = result.encode()
        obj.result_len = len(result)
        obj.total_len += obj.result_len
        return obj
