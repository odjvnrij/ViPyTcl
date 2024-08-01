import logging
import os
from .utils import my_logger as _my_logger
from .base import *
from .core import TclProcessPopen
from .core import VivadoPrj
from .core import DefaultVivadoBatPath, find_vivado_bat
from .core import GRPCServer, GRPCRemoteTclServicer, RemoteTclProcessPopen, add_RemoteTclServicer_to_server

__all__ = ["VivadoPrj",
           "TclProcessPopen",
           "program_bits",
           "tcl",
           "terminate",
           "viproperty",
           "DefaultVivadoBatPath", "GRPCServer", "RemoteTclProcessPopen", "GRPCRemoteTclServicer",
           "add_RemoteTclServicer_to_server"]

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
    _tcl_popen.tcl("\n".join(("open_hw_manager",
                              "connect_hw_server",
                              "open_hw_target",
                              "current_hw_device [lindex [get_hw_devices] 0]",
                              "refresh_hw_device -update_hw_probes false [current_hw_device]",
                              f"set_property PROGRAM.FILE {{{bit_path}}} [current_hw_device]",
                              "program_hw_devices [current_hw_device]",
                              "close_hw_manager")))


def tcl(cmd: str, vivado_bat_path: str = ""):
    vivado_bat_path = vivado_bat_path if vivado_bat_path else DefaultVivadoBatPath

    global _tcl_popen
    if not _tcl_popen:
        _tcl_popen = TclProcessPopen(vivado_bat_path, output=True)

    return _tcl_popen.tcl(cmd)


def terminate():
    global _tcl_popen
    if _tcl_popen:
        _tcl_popen.terminate()
        _tcl_popen = None


def remote_tcl_server(ip="127.0.0.1", port=21000):
    grpc_server = GRPCServer()
    remote_tcl_servicer = GRPCRemoteTclServicer()
    grpc_server.add_servicer(add_RemoteTclServicer_to_server, remote_tcl_servicer)
    grpc_server.add_stop_callback(remote_tcl_servicer.stop)
    grpc_server.add_aps_job(remote_tcl_servicer.clean_vivado_cache, "interval", days=3)
    grpc_server.add_aps_job(remote_tcl_servicer.clean_file_cache, "interval", days=3)

    grpc_server.add_insecure_port(ip, int(port))
    grpc_server.start()


def remote_program_bits(bit_path: str, ip="127.0.0.1", port=21000):
    _vivado = VivadoPrj(server_addr=(ip, port))
    bit_path = _vivado.grpc_put_file(bit_path)
    _vivado.program_bits(bit_path)
    _vivado.exit()
