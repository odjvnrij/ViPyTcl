import os
from .core.tcl_process import TclProcessPopen
from .core.vivado_prj import VivadoPrj
from .core.global_var import DefaultVivadoBatPath, find_vivado_bat
from .base import *

__all__ = ["VivadoPrj", "TclProcessPopen", "program_bits", "tcl", "terminate", "viproperty", "DefaultVivadoBatPath"]

__author__ = "odjvnrij <odjvnrij72@outlook.com>"
__status__ = "production"
# The following module attributes are no longer updated.
__version__ = "1.0"
__date__ = "03 April 2024"

_tcl_popen = None  # type: TclProcessPopen or None


def program_bits(bits_path: str, vivado_bat_path: str = ""):
    vivado_bat_path = vivado_bat_path if vivado_bat_path else DefaultVivadoBatPath

    global _tcl_popen
    if not _tcl_popen:
        _tcl_popen = TclProcessPopen(vivado_bat_path, output=True)

    if not os.path.exists(bits_path):
        raise FileNotFoundError(f"bit file not found: {bits_path}")

    bit_path = bits_path.replace("\\", "/")
    _tcl_popen.run("".join(("open_hw_manager",
                            "connect_hw_server",
                            "open_hw_target",
                            "current_hw_device [lindex [get_hw_devices] 0]",
                            "refresh_hw_device -update_hw_probes false [current_hw_device]",
                            f"set_property PROGRAM.FILE {bit_path} [current_hw_device]",
                            "program_hw_devices [current_hw_device]",
                            "close_hw_manager")))


def tcl(cmd: str, vivado_bat_path: str = ""):
    vivado_bat_path = vivado_bat_path if vivado_bat_path else DefaultVivadoBatPath

    global _tcl_popen
    if not _tcl_popen:
        _tcl_popen = TclProcessPopen(vivado_bat_path, output=True)

    return _tcl_popen.run(cmd)


def terminate():
    global _tcl_popen
    if _tcl_popen:
        _tcl_popen.terminate()
        _tcl_popen = None
