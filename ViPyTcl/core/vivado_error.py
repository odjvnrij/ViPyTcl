import re
from enum import Enum


class VivadoErrorType(Enum):
    Vi = 0
    Common = 1
    Vivado = 2


class VivadoError(Exception):
    """ Vivado错误基类, 从Vivado捕获的错误将直接继承这个类"""

    def __init__(self, error_type: VivadoErrorType, code: str, message: str):
        self.type = error_type
        self.code = code
        self.message = message

    def __str__(self):
        return f"[{self.type} {self.code}] {self.message}"


class ViError(VivadoError):
    """代码中的错误类，不是Vivado的错误累"""

    def __init__(self, message: str, error_type: VivadoErrorType = VivadoErrorType.Vi, code: str = "\b"):
        self.message = message
        super().__init__(error_type=error_type, code=code, message=message)


class ViArgsError(ViError):
    pass


class ViUnexit(ViError):
    pass


class ViRunNotExist(ViError):
    pass


class ViUnknownRunType(ViError):
    pass


class ViRunNameDontMatch(ViError):
    pass


class ViNotInRightDesign(ViError):
    pass


class ViTclCantRunError(ViError):
    pass


class ViUnexpectedEmptyTclReturnError(ViError):
    pass


class ViNoPrjFoundError(ViError):
    pass


class ViNoSuchProperty(ViError):
    pass


class ViUnknownPropertyValue(ViError):
    pass


CommonErrDict = {
    "Common 17-162": ViRunNotExist
}


def get_err_from_str(s: str):
    t = re.search(r"^ERROR: \[(?P<error_type>\w+) (?P<code>[\d\-]+)\] (?P<message>.*)", s)

    err = CommonErrDict.get(f'{t.group("error_type")} {t.group("code")}', None)
    if not err:
        return VivadoError(t.group("error_type"), t.group("code"), t.group("message"))
    else:
        return err(message=t.group("message"), error_type=t.group("error_type"), code=t.group("code"))
