import os.path
from enum import IntEnum
from .vivado_error import ViError


class MsgStat(IntEnum):
    Receive = 0x01
    Run = 0x02
    Done = 0x10
    Fail = 0x11
    Timeout = 0x12
    FileNotFound = 0x15


class GRPCErrCode(IntEnum):
    TclRunErr = 0x01
    TclRunTimeoutErr = 0x02
    FileNotFoundErr = 0x5
    FileExistsErr = 0x6
    UnknownErr = 0x50


class GRPCErr(Exception):
    pass


GRPCErrCode2Err = {
    GRPCErrCode.TclRunErr: ViError,
    GRPCErrCode.FileNotFoundErr: FileNotFoundError,
    GRPCErrCode.FileExistsErr: FileExistsError,
    GRPCErrCode.UnknownErr: GRPCErr,
}
