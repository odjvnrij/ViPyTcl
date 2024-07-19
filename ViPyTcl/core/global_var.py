import os
import re


def find_vivado_bat() -> str:
    import sys
    if sys.platform != "win32":
        raise OSError("Only support windows platform")

    if os.path.exists("C:\\Xilinx\\Vivado"):
        for f in os.scandir("C:\\Xilinx\\Vivado"):
            if f.is_dir() and re.findall(r"\d+\.\d+", f.name):
                bat_path = os.path.join(f.path, "bin", "vivado.bat")
                if os.path.exists(bat_path):
                    return bat_path

    return ""


DefaultVivadoBatPath = find_vivado_bat()
