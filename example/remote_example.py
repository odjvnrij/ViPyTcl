from apscheduler.triggers.interval import IntervalTrigger
import time
import logging

from ViPyTcl import GRPCServer, GRPCRemoteTclServicer, add_RemoteTclServicer_to_server, VivadoPrj
from ViPyTcl.core import clean_file_cache, clean_vivado_cache

logger = logging.getLogger("ViPyTcl")


def run_server(port: int = 16000):
    grpc_server = GRPCServer()
    remote_tcl_servicer = GRPCRemoteTclServicer()
    grpc_server.add_servicer(add_RemoteTclServicer_to_server, remote_tcl_servicer)
    grpc_server.add_stop_callback(remote_tcl_servicer.stop)
    grpc_server.add_aps_job(clean_vivado_cache, trigger=IntervalTrigger(days=3))
    grpc_server.add_aps_job(clean_file_cache, trigger=IntervalTrigger(days=3))

    grpc_server.add_insecure_port("127.0.0.1", port)
    grpc_server.start()

    while True:
        time.sleep(1000)


def run_client(port: int = 16000):
    client = VivadoPrj(server_addr=('127.0.0.1', port))

    # both way to create a remote tcl process
    # VivadoPrj will provide more useful function like get_cells, get_nets, etc.
    # client = RemoteTclProcessPopen(ip='127.0.0.1', port=port)

    client.tcl("puts {Remote hello world}")
    client.tcl("set a 10")
    client.tcl("set b 20")
    result = client.tcl("expr [expr $a + $b]")[0]
    print(f"result: {result}")
    client.exit()


if __name__ == '__main__':
    mode = input("mode: ")
    p = input("port: ")
    p = int(p) if p else 16000

    if mode in ("s", "server"):
        run_server(p)
    else:
        run_client(p)
