import re
import time


def format_bytes(byte: bytes):
    return "_".join([f"{b:02X}" for b in byte])


def format_int(value: int):
    return "%08X" % value


def format_path(path: str):
    return path.replace("\\", "/")


def sleep(sec: int or str):
    if isinstance(sec, str):
        sec = get_sec_from_time_str(sec)
        time.sleep(sec)
    else:
        time.sleep(sec)


def get_sec_from_time_str(time_str: str):
    """
    Convert time str to sec
    :param time_str: time str
    :return: sec
    """
    time_str = time_str.lower()
    n, t = re.findall(r"([\.\d]+)(.*)", time_str)[0]
    if not n or n == "0":
        return 0

    n_type = float if "." in n else int
    if t in ("s", ""):
        return n_type(n)
    elif t in ("m", "min"):
        return n_type(n) * 60
    elif t in ("h", "hour"):
        return n_type(n) * 3600
    else:
        return 0
