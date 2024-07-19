import logging
import subprocess
import threading
import traceback
import socket
import queue

from ..base.msg import *
from .tcl_process import TclProcessPopen, DontDoPutsCmd, BaseTclProcess
from . import tools

logger = logging.getLogger()


class RemoteTclServer(TclProcessPopen):
    def __init__(self,
                 ip: str,
                 port: int,
                 vivado_bat_path: str = "", timeout: int = 10, max_client: int = 5,
                 *args, output=False, save_log: str = "", clean=True, error_check=True,
                 encode="GBK",
                 escape=(), shell=True, output_stdout=False,
                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,
                 **kwargs):
        self.ip = ip
        self.port = int(port)
        self.addr = (self.ip, self.port)
        self._max_client = max_client
        self._timeout = timeout
        self._is_open = False
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._socket.bind(self.addr)
        self._socket.listen(self._max_client)
        self._socket.settimeout(self._timeout)
        self._client = {}
        self._exec_th = None
        self._listen_th = None
        self._msg_queue = queue.Queue(1024)

        super().__init__(
            vivado_bat_path=vivado_bat_path,
            output=output,
            save_log=save_log,
            clean=clean,
            error_check=error_check,
            encode=encode,
            escape=escape, shell=shell, output_stdout=output_stdout,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            delay=True,
            *args,
            **kwargs
        )

    def open(self):
        super().open()
        self._is_open = True
        self._listen_th = threading.Thread(target=self._tcp_listen)
        self._exec_th = threading.Thread(target=self._exec)
        self._listen_th.start()
        self._exec_th.start()

    def _exec(self):
        logger.info(f"tcl exec thread on")
        while self._is_open:
            try:
                cmd_req = self._msg_queue.get(block=True, timeout=self._timeout)  # type: CmdReqMsg

                cmd = cmd_req.cmd.decode()

                logger.info(f"Queue {cmd_req.addr} -> exec: {cmd_req.cmd}")
                output = self.run(cmd, timeout=cmd_req.timeout)
                logger.debug(f"exec {cmd}, result: {output}")

                conn = self._client.get(cmd_req.addr, None)  # type: socket.socket
                if conn is None:
                    logger.warning(f"client disconnected when try to resp, addr: {cmd_req.addr}")
                    continue

                output = "\n".join(output) if output else ""

                resp_msg = CmdRespMsg.from_req(cmd_req, output)

                logger.debug(f"send resp: {output}, {tools.format_bytes(resp_msg.get_bytes())}")
                conn.sendall(resp_msg.get_bytes())

            except queue.Empty:

                if self._is_open:
                    continue
                else:
                    logger.info("stop run, tcl exec thread quit")
                    break

            except Exception as err:
                logger.error("tcl exec thread error")
                logger.error(traceback.format_exc())
                continue

    def _tcp_listen(self):
        logger.info(f"tcp listen thread on")
        while self._is_open:
            try:
                conn, addr = self._socket.accept()
            except socket.timeout as e:
                if self._is_open:
                    continue
                else:
                    logger.info("stop run, tcp listen thread quit")
                    break

            self._client[addr] = conn
            logger.info(f"tcp conn established: {addr}")
            hdlr = threading.Thread(target=self._tcp_recv, args=(conn, addr), daemon=False)
            hdlr.start()

    def _tcp_recv(self, conn: socket.socket, addr: tuple):
        logger.info(f"tcp recv thread on {addr}")
        while self._is_open:
            try:
                recv_data = conn.recv(16)
                logger.debug(f"get len: {len(recv_data)}, bytes: {tools.format_bytes(recv_data)}")
                if len(recv_data) != 16 or int.from_bytes(recv_data[0:4], "big") != 1414812756:
                    print(int.from_bytes(recv_data[0:4], "big") != 0x1414812756, int.from_bytes(recv_data[0:4], "big"))
                    continue

                msg_len = int.from_bytes(recv_data[4:8], "big")
                msg_type = int.from_bytes(recv_data[8:10], "big")
                big_ver = recv_data[10]
                little_ver = recv_data[11]
                res = recv_data[12:16]
                logger.debug(f"get header: {tools.format_bytes(recv_data)}, len:{msg_len}, type:{msg_type}")

                if msg_len - 16 < 0:
                    logger.debug(f"tcp recv invalid msg len: {msg_len}")
                    continue

                try:
                    tcp_msg_type = TclMsgType(msg_type)
                except ValueError:
                    logger.debug(f"tcp recv invalid msg type: {msg_type}")
                    continue

                if tcp_msg_type is TclMsgType.CmdReq:
                    req_cmd = conn.recv(msg_len - 16)
                    timeout = int.from_bytes(req_cmd[0:3], "big")
                    stat = req_cmd[3]

                    if msg_len > 20:
                        cmd = req_cmd[4:].decode()
                    else:
                        cmd = ""

                    req_msg = CmdReqMsg(addr, cmd=cmd, stat=stat, timeout=timeout)
                    self._msg_queue.put(req_msg, block=True)

                    logger.debug(
                        f"tcp {req_msg.addr} -> Queue, type:{req_msg.msg_type.name}, len:{req_msg.cmd_len}, cmd: {cmd}")
                else:
                    continue

            except ConnectionResetError as err:
                logger.info(f"tcp conn disconnect: {conn.getpeername()}")
                break

            except socket.timeout:
                if self._is_open:
                    continue
                else:
                    logger.info("stop run, tcp recv thread quit")
                    break

            except Exception as err:
                logger.error("tcp recv thread error")
                logger.error(traceback.format_exc())
                raise err

        conn.close()


class RemoteTclProcessPopen(BaseTclProcess):
    def __init__(self, server_ip: str, server_port: int, timeout: int = 5, *args, **kwargs):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = int(server_port)
        self.server_addr = (self.server_ip, self.server_port)
        self._timeout = int(timeout) if timeout else 5
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._is_open = False
        self._recv_th = None
        self._resp_event = threading.Event()

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: int):
        self._timeout = int(timeout)
        if self._socket:
            self._socket.settimeout(self._timeout)

    def open(self):
        self._socket.connect(self.server_addr)
        self._socket.settimeout(self.timeout)
        self._is_open = True

        self._recv_th = threading.Thread(target=self._recv)
        self._recv_th.start()

    def _send_cmd(self, tcl: str, raw: bool = False) -> None:
        tcl_type = tcl.split()[0]

        self._cur_cmd_done.clear()
        self._cur_cmd = tcl
        escape_tcl = self._escape_tcl(self._cur_cmd)

        cmd = f'puts "\[Tcl run\] {escape_tcl}"\n'

        if raw or (tcl_type in DontDoPutsCmd):
            cmd += f"{tcl}\n"
        else:
            cmd += f'puts [{tcl}]\n'

        cmd += f'puts "\[Tcl end\]"'

        cmd_req = CmdReqMsg(self.server_addr, tcl, timeout=self._timeout)

        logger.debug(f"tcl send cmd: {cmd}")
        b = cmd_req.get_bytes()
        self._socket.sendall(b)
        logger.debug(f"send bytes len{len(b)}: {tools.format_bytes(b)}")

    def _recv(self):
        logger.debug(f"tcp recv thread on {self.server_addr}")
        while True:
            try:
                recv_data = self._socket.recv(16)
                if len(recv_data) != 16 or int.from_bytes(recv_data[0:4], "big") != 1414812756:
                    continue

                msg_len = int.from_bytes(recv_data[4:8], "big")
                msg_type = int.from_bytes(recv_data[8:10], "big")
                big_ver = recv_data[10]
                little_ver = recv_data[11]
                res = recv_data[12:16]

                logger.debug(f"get header: {tools.format_bytes(recv_data)}, len:{msg_len}, type:{msg_type}")

                if msg_len - 16 < 0:
                    logger.debug(f"tcp recv invalid msg len: {msg_len}")
                    continue

                try:
                    msg_type = TclMsgType(msg_type)
                except ValueError:
                    logger.debug(f"tcp recv invalid msg type: {msg_type}")
                    continue

                if msg_type is TclMsgType.CmdResp:
                    req_cmd = self._socket.recv(msg_len - 16)
                    timeout = int.from_bytes(req_cmd[0:3], "big")
                    stat = req_cmd[3]

                    if msg_len > 20:
                        result = req_cmd[4:].decode()
                    else:
                        result = ""

                    if result:
                        self._cur_out = result.split("\n")
                    else:
                        self._cur_out = []

                    self._cur_cmd_done.set()

                    logger.debug(
                        f"tcp {self.server_addr} -> this, type:{msg_type}, len:{msg_len}, cmd: {self._cur_cmd}, result:{result}")
                else:
                    continue

            except ConnectionAbortedError:
                logger.info(f"tcp conn disconnect: {self._socket.getpeername()}")
                break

            except (socket.timeout, OSError):
                if self._is_open:
                    continue
                else:
                    break

            except Exception as err:
                logger.error("tcp recv thread error")
                logger.error(traceback.format_exc())
                raise err
        self._socket.close()

    def run(self, tcl, raw: bool = False, timeout: int = None) -> list:
        return super().run(tcl, raw, None)
