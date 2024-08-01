import logging
import os
import sys
import time
import traceback
from concurrent import futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Union

import apscheduler.schedulers.background
import grpc

from . import remote_tcl_pb2
from .remote_tcl_pb2_grpc import RemoteTclServicer, RemoteTclStub, RemoteTcl, add_RemoteTclServicer_to_server
from ..base.remote_base import *
from .tcl_process import TclProcessPopen, BaseTclProcess

logger = logging.getLogger("ViPyTcl")


def clean_file_cache(cache, expire_days: int = 15):
    if not os.path.isdir(cache):
        return
    logger.info("APS start file cache clean")
    file, folder = 0, 0
    current_time = datetime.now()
    expire = current_time - timedelta(days=expire_days)

    try:
        # 遍历当前目录下的所有文件和子目录
        for root, dirs, files in os.walk(cache, topdown=False):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                # 获取文件的修改时间
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                # 如果文件修改时间早于30天前，删除文件
                if mtime < expire:
                    os.remove(file_path)
                    file += 1

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                # 如果子目录下没有文件，删除该子目录
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    folder += 1

    except OSError as e:
        logger.error(f"Error: {e}")

    logger.info(f"file cache clean done, file: {file}, dir: {folder}")


def ipv4_parser(ip_str: str) -> Tuple[str, int]:
    """
    将grpc中的ip_str: "ipv4:127.0.0.1:8440" 的ip和port信息解析出来
    :param ip_str:
    :return:
    """
    _ = ip_str.split(":")
    return _[1], int(_[2])


class GRPCServer:
    def __init__(self, worker: int = 10, use_aps: bool = True):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=worker))
        self._is_run = False
        if use_aps:
            self._aps = apscheduler.schedulers.background.BackgroundScheduler(timezone='Asia/Shanghai')
        else:
            self._aps = None
        self._stop_callback = {}

    def add_aps_job(self, *args, **kwargs):
        self._aps.add_job(*args, **kwargs)

    def add_servicer(self, add_servicer_func, servicer):
        add_servicer_func(servicer, self._server)
        logger.info(f"GRPC Server add servicer {servicer.__class__.__name__}")

    def add_insecure_port(self, ip: str, port: int):
        use_port = self._server.add_insecure_port(f'{ip}:{int(port)}')
        logger.info(f"GRPC Server add insecure port {ip}:{use_port}")
        return use_port

    def add_stop_callback(self, func, args: tuple = (), kwargs: dict = None):
        kwargs = kwargs if kwargs else {}
        self._stop_callback[func] = (args, kwargs)

    def start(self):
        if self._is_run:
            return
        self._aps.start()
        self._server.start()
        self._is_run = True
        logger.info("GRPC Server start")

    def stop(self):
        if not self._is_run:
            return

        logger.info("GRPC Server stop ...")
        for func, _ in self._stop_callback.items():
            func(*_[0], **_[1])

        if self._aps.running:
            self._aps.shutdown()

        self._server.stop(0)
        self._is_run = False
        logger.info("GRPC Server stop done")


class GRPCRemoteTclServicer(RemoteTclServicer):
    def __init__(self, *args, **kwargs):
        self._tcl_proc = TclProcessPopen(*args, error_check=False, **kwargs)  # type: TclProcessPopen or None
        self._cache = Path(".cache")
        self._cache.mkdir(exist_ok=True)

    def stop(self):
        self._tcl_proc.terminate()

    def tcl(self, request, context):
        logger.info(
            f"tcl request from {ipv4_parser(context.peer())}: '{request.cmd}', raw: {request.raw}, timeout: {request.timeout}, block: {request.block}")

        try:
            output = self._tcl_proc.tcl(request.cmd, timeout=request.timeout, raw=request.raw, block=request.block)
            output = "\n".join(output)
            stat = MsgStat.Done
            err = 0
            err_info = ""

            resp = ("-" * 20 + "\n" + output + "\n" + "-" * 20) if output else ("-" * 20 + "\n" + "-" * 20)
            logger.debug(
                f"tcl resp to {ipv4_parser(context.peer())}: \n{resp}")

        except TimeoutError as err:
            err_info = f"tcl exec timeout {request.timeout}: '{request.cmd}'"
            logger.error(err_info)
            stat = MsgStat.Timeout
            err = GRPCErrCode.TclRunTimeoutErr
            output = ""

        except Exception as err:
            logger.error(
                f"tcl exec failed: '{request.cmd}'"
            )
            stat = MsgStat.Fail
            err = GRPCErrCode.UnknownErr
            err_info = traceback.format_exc()
            output = ""
            logger.error(err_info)

        return remote_tcl_pb2.TclResponse(cmd=request.cmd, output=output, raw=request.raw,
                                          timeout=request.timeout, block=request.block,
                                          common=remote_tcl_pb2.Common(stat=stat.value, err=err, err_info=err_info))

    def put_file(self, request, context):
        addr = ipv4_parser(context.peer())
        logger.debug(
            f"put file request from {addr}: size: {request.size}, {request.src_path} -> {request.dst_path}, ")
        src = Path(request.src_path)
        dst = Path(request.dst_path)

        try:
            if dst.is_absolute():
                if not dst.parent.exists():
                    raise FileNotFoundError

                elif dst.is_dir():
                    dst = dst / src.name

            else:
                dst = self._cache / f"{addr[0]}_{addr[1]}" / dst
                if dst.is_dir():
                    dst = dst / src.name
                os.makedirs(dst.parent, exist_ok=True)

            dst = dst.absolute()
            with open(dst, "wb") as f:
                f.write(request.content)
            size = os.path.getsize(dst)

            stat = MsgStat.Done
            err = 0
            err_info = ""
            logger.debug(f"put file req from {ipv4_parser(context.peer())}: {src} -> {dst}, size: {size}")

        except FileNotFoundError as err:
            logger.error(
                f"put file failed, file not found: {request.src_path} -> {request.dst_path}"
            )
            size = 0
            stat = MsgStat.Fail
            err = GRPCErrCode.FileNotFoundErr
            err_info = traceback.format_exc()
            logger.error(err_info)

        except Exception as err:
            logger.error(
                f"put file failed: {request.src_path} -> {request.dst_path}"
            )
            size = 0
            stat = MsgStat.Fail
            err = GRPCErrCode.UnknownErr
            err_info = traceback.format_exc()
            logger.error(err_info)

        logger.debug(
            f"put file resp from {ipv4_parser(context.peer())}: {src} <- {dst}, size: {size}")
        return remote_tcl_pb2.PutFileResponse(src_path=request.src_path,
                                              dst_path=str(dst),
                                              size=size,
                                              common=remote_tcl_pb2.Common(stat=stat.value, err=err, err_info=err_info))

    def get_file(self, request, context):
        addr = ipv4_parser(context.peer())
        logger.debug(
            f"get file request from {addr}: {request.dst_path} <- {request.src_path}, ")
        src = Path(request.src_path)

        try:
            if src.is_absolute() and not src.is_file():
                raise FileNotFoundError
            else:
                src = self._cache / "-".join(addr) / src
                if not os.path.isfile(src):
                    raise FileNotFoundError

            with open(src, "rb") as f:
                file_bytes = f.read()
                file_bytes_len = len(file_bytes)

            src = src.absolute()
            stat = MsgStat.Done
            err = 0
            err_info = ""
            logger.debug(
                f"get file req from {ipv4_parser(context.peer())}: {request.dst_path} <- {src}, size: {file_bytes_len}")

        except FileNotFoundError as err:
            logger.error(
                f"put file failed, file not found: {request.src_path} -> {request.dst_path}"
            )
            file_bytes = b""
            file_bytes_len = 0
            stat = MsgStat.Fail
            err = GRPCErrCode.FileNotFoundErr
            err_info = traceback.format_exc()
            logger.error(err_info)

        except Exception as err:
            logger.error(
                f"get file failed: {request.dst_path} <- {request.src_path}"
            )
            file_bytes = b""
            file_bytes_len = 0
            stat = MsgStat.Fail
            err = GRPCErrCode.UnknownErr
            err_info = traceback.format_exc()
            logger.error(err_info)

        logger.debug(f"resp get file, {request.dst_path} <- {request.src_path}", )
        return remote_tcl_pb2.GetFileResponse(
            src_path=str(src),
            dst_path=request.dst_path,
            size=file_bytes_len, content=file_bytes,
            common=remote_tcl_pb2.Common(stat=stat.value, err=err, err_info=err_info))


class RemoteTclProcessPopen(BaseTclProcess):
    def __init__(self, ip: str, port: int, delay: bool = False):
        super().__init__()
        self.server_ip = ip
        self.server_port = int(port)

        self._is_open = False
        self._channel = None
        self._client = None
        if not delay:
            self.open()

    @staticmethod
    def _check_grpc_resp_err(response):
        if response.common.err:
            err = GRPCErrCode2Err.get(response.common.err)
            err_info = response.common.err_info
            raise err(err_info)

    def open(self):
        if self._is_open:
            return

        super().open()
        self._channel = grpc.insecure_channel(f"{self.server_ip}:{self.server_port}")
        self._channel.__enter__()
        self._client = RemoteTclStub(channel=self._channel)
        self._is_open = True

    def terminate(self):
        super().terminate()
        self._channel.__exit__(None, None, None)

    def _send_cmd(self, tcl: str, raw: bool = False, timeout: int = 0, block: bool = True):
        timeout = int(timeout) if timeout else 0

        req = remote_tcl_pb2.TclRequest(cmd=tcl, raw=bool(raw), timeout=timeout, block=block,
                                        common=remote_tcl_pb2.Common(stat=MsgStat.Receive.value))
        response = self._client.tcl(req)
        self._check_grpc_resp_err(response)

        if response.output:
            output = response.output.split("\n")
        else:
            output = []
        logger.info(f"run tcl: {tcl}")
        return output

    def grpc_put_file(self, src_path, dst_path: str = "", timeout: int = 0) -> Union[str, Path]:
        """ 将本机src_path文件发送到远端dst_path文件 """
        start = time.time()
        logger.info(f"request put file {src_path} -> {dst_path}")
        if not os.path.isfile(src_path):
            raise FileNotFoundError

        with open(src_path, "rb") as f:
            file_bytes = f.read()
        file_bytes_len = len(file_bytes)

        response = self._client.put_file(
            remote_tcl_pb2.PutFileRequest(src_path=src_path,
                                          dst_path=dst_path,
                                          size=file_bytes_len,
                                          content=file_bytes,
                                          common=remote_tcl_pb2.Common(stat=MsgStat.Receive.value)))
        self._check_grpc_resp_err(response)
        time_usage = time.time() - start
        logger.info(
            f"response put file {src_path} -> {dst_path}, file_size: {file_bytes_len}, send_size: {response.size}, time_usage: {time_usage:.2f} s, speed: {file_bytes_len / time_usage / 1024:.2f} KB/s")
        return response.dst_path

    def grpc_get_file(self, src_path, dst_path: str = "", timeout: int = 0) -> Union[str, Path]:
        """ 将远端src_path文件发送到本机dst_path文件 """
        start = time.time()
        logger.info(f"request get file {dst_path} <- {src_path}")
        response = self._client.get_file(
            remote_tcl_pb2.GetFileRequest(src_path=src_path,
                                          dst_path=dst_path,
                                          common=remote_tcl_pb2.Common(stat=MsgStat.Receive.value)))
        self._check_grpc_resp_err(response)

        dst_path = Path(dst_path)
        src_path = Path(src_path)

        if dst_path.is_absolute():
            if not dst_path.parent.exists():
                raise FileNotFoundError

            elif dst_path.is_dir():
                dst_path = dst_path / src_path.name

        else:
            if dst_path.is_dir():
                dst_path = dst_path / src_path.name
            os.makedirs(dst_path.parent, exist_ok=True)

        dst_path = dst_path.absolute()
        with open(dst_path, "wb") as f:
            f.write(response.content)
        file_bytes_len = os.path.getsize(dst_path)
        if file_bytes_len != response.size:
            logger.warning(f"get file size dont match, file_size: {file_bytes_len}, recv_size: {response.size}")

        time_usage = time.time() - start
        logger.info(
            f"request get file {dst_path} <- {src_path}, file_size: {file_bytes_len}, recv_size: {response.size}, time_usage: {time_usage:.2f} s, speed: {file_bytes_len / time_usage / 1024:.2f} KB/s")
        return dst_path
