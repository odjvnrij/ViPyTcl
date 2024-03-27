import os
import subprocess
import shutil
import threading
import re

def search_vivado_bat_path() -> str:
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

class TclProcessPopen(subprocess.Popen):
    def __init__(self, vivado_bat_path: str = "", *args, output=False, save_log: str = "", clean=True, encode="GBK",
                 escape=(), shell=True,
                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,
                 **kwargs):
        self._vivado_bat_path = vivado_bat_path if vivado_bat_path else search_vivado_bat_path()
        if not self._vivado_bat_path or not os.path.exists(self._vivado_bat_path):
            raise FileNotFoundError(f"Can't find vivado.bat, {self._vivado_bat_path}")

        super().__init__([vivado_bat_path, "-mode", "tcl"], *args, shell=shell, stdin=stdin, stdout=stdout,
                         stderr=stderr, **kwargs)
        self._cache = os.getcwd()
        self._output = output
        self._clean = clean
        self._save_log = save_log
        self._escape = ("\\", "[", "]", "$", "{", "}", '"', *escape)
        self._encode = encode
        self._log = ""
        self._log_path = os.path.join(self._cache, "vivado.log")

        self._is_recv = True
        self._is_cur_out = False
        self._is_terminate = False
        self._cur_cmd = None  # type: str or None
        self._cur_out = []
        self._cur_cmd_done = threading.Event()
        self._lock = threading.Lock()

        self._recv_th = threading.Thread(target=self._recv_th)
        self._recv_th.start()

    def clean_vivado_cache(self) -> None:
        """
        清理vivado运行的缓存文件
        :return:
        """
        for f in os.scandir(self._cache):
            if re.findall(r"vivado[_\d]*\.(backup\.)?\.(jou|jou)", f.name) and f.is_file():
                os.remove(f.path)
            elif f.name == ".Xil" and f.is_dir():
                shutil.rmtree(f.path)

    def save_log(self, path: str) -> None:
        """
        保存缓存文件
        :param path:
        :return:
        """
        shutil.copy(self._log, path)

    def terminate(self) -> None:
        """
        终止进程，最好在使用后调用
        :return:
        """
        self._is_recv = False
        self._is_terminate = True
        super().communicate()
        super().terminate()

        if self._save_log:
            if not os.path.exists(self._save_log):
                self.save_log(self._save_log)
            elif os.path.isdir(self._save_log):
                self.save_log(os.path.join(self._save_log, os.path.basename(self._log)))
            else:
                raise FileExistsError(f"{self._save_log} is exists")

        if self._clean:
            self.clean_vivado_cache()

    def _recv_th(self):
        while self._is_recv:
            s = self.stdout.readline().decode(self._encode)

            if self._output and s:
                print("#", s.strip("\n"))

            if not self._cur_cmd:
                continue

            ret = re.findall(r"^\[tcl (return|run)] .*", s)
            if ret:
                ret = ret[0]
                if ret == "run":
                    self._is_cur_out = True

                elif ret == "return":
                    self._is_cur_out = False
                    self._cur_cmd = None
                    self._cur_cmd_done.set()

            elif self._is_cur_out:
                self._cur_out.append(s.strip(os.linesep))

    def _escape_tcl(self, s: str) -> str:
        """
        转义tcl语句
        :param s:
        :return:
        """
        for esc in self._escape:
            s = s.replace(esc, f"\\{esc}")
        return s

    def _write_2_stdin(self, tcl) -> None:
        if not tcl.endswith("\n"):
            tcl += "\n"
        self.stdin.write(tcl.encode())
        self.stdin.flush()

    def _send_cmd(self, tcl: str) -> None:
        """
        发送tcl语句
        :param tcl:
        :return:
        """
        self._cur_cmd = tcl.strip(" ").strip("\n")
        escape_tcl = self._escape_tcl(tcl)
        self._write_2_stdin(f'puts "\[tcl run\] {escape_tcl}"')
        self._write_2_stdin(tcl)
        self._write_2_stdin(f'puts "\[tcl return\] {escape_tcl}"')

    def run(self, tcl) -> list:
        """
        阻塞方式运行tcl语句，完成后返回输出的信息列表
        :param tcl:
        :return:
        """
        self._lock.acquire()

        self._send_cmd(tcl)
        self._cur_cmd_done.wait()

        output, self._cur_out = self._cur_out, []
        self._cur_cmd_done.clear()
        self._lock.release()
        return output
