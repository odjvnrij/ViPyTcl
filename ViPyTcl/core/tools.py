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


def get_clk_cnt_from_time_str(time_str: str, ref_clk_mhz: int = 50):
    """
    Convert time str to cnt
    :param time_str: time str
    :param ref_clk_mhz: ref clk mhz
    :return: cnt
    """
    time_str = time_str.lower()
    if not time_str:
        return 0

    n, t = re.findall(r"([\d\.]+)(.*)", time_str)[0]
    if not n or n == "0":
        return 0

    n = float(n)
    if t in ("s", ""):
        return int(n * ref_clk_mhz * 1e6)
    elif t in ("ms",):
        return int(n * ref_clk_mhz * 1e3)
    elif t in ("us",):
        return int(n * ref_clk_mhz)
    elif t in ("ns",):
        return int(n * ref_clk_mhz / 1e3)


def get_time_str_from_clk_cnt(clk_cnt: int, ref_clk_mhz: int = 50):
    """
    将 clk_cnt 转换为 time_str（5us， 1ms）
    :param clk_cnt:
    :return:
    """
    if clk_cnt == 0:
        return "0s"
    elif clk_cnt < 50:
        return f"%.3fns" % (clk_cnt * 1e3 / ref_clk_mhz)
    elif 50 <= clk_cnt < 50e3:
        return f"%.3fus" % (clk_cnt / ref_clk_mhz)
    elif 50e3 <= clk_cnt < 50e6:
        return f"%.3fms" % (clk_cnt / ref_clk_mhz / 1e3)
    else:
        return f"%.3fs" % (clk_cnt / ref_clk_mhz / 1e6)


def get_mul_num_from_sample_time(sampling_time: str, ref_clk_mhz: int = 50):
    """
    将 sampling_time（5us， 1ms） 转换为 cnt 到 freq 的倍数
    :param sampling_time:
    :return:
    """
    sampling_time = sampling_time.lower()
    return int(get_clk_cnt_from_time_str("1s", ref_clk_mhz) / get_clk_cnt_from_time_str(sampling_time, ref_clk_mhz))


if __name__ == '__main__':
    b = get_clk_cnt_from_time_str("0s")
    a = get_time_str_from_clk_cnt(b)
    print(a, "->", b)

    for i in range(0, 9):
        b = get_clk_cnt_from_time_str("%dus" % 10 ** i)
        a = get_time_str_from_clk_cnt(b)
        print(f"[{i}]", a, "->", b)
