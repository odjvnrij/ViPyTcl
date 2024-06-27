import os
import re
import shutil
import subprocess
import threading
import traceback

from .vivado_error import VivadoError

DontDoPutsCmd = {"puts", "for", "foreach", "while", "source"}


class TclProcessPopen(subprocess.Popen):
    def __init__(self, vivado_bat_path: str, *args, output=False, save_log: str = "", clean=True, error_check=True,
                 encode="GBK",
                 escape=(), shell=True, output_stdout=False,
                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,
                 **kwargs):
        self._vivado_bat_path = vivado_bat_path
        if not self._vivado_bat_path or not os.path.exists(self._vivado_bat_path):
            raise FileNotFoundError(f"Can't find vivado.bat, {self._vivado_bat_path}")

        self._major_cmd = ["%SystemRoot%\system32\cmd.exe", "/k", self._vivado_bat_path, "-mode", "tcl"]
        super().__init__(self._major_cmd, *args, shell=shell,
                         stdin=stdin, stdout=stdout, stderr=stderr, **kwargs)
        self._cache = os.getcwd()
        self._output = output
        self._output_stdout = output_stdout
        self._clean = clean
        self._error_check = error_check
        self._save_log = save_log
        self._escape = ("\\", "[", "]", "$", "{", "}", '"', *escape)
        self._encode = encode
        self._log_path = os.path.join(self._cache, "vivado.log")
        self._jou_path = os.path.join(self._cache, "vivado.jou")

        self._is_recv = True
        self._is_cur_out = False
        self._is_terminate = False
        self._cur_cmd = None  # type: str or None
        self._cur_out = []
        self._cur_err = None
        self._cur_cmd_done = threading.Event()
        self._lock = threading.Lock()

        self._recv_th_obj = threading.Thread(target=self._recv_th, daemon=True)
        self._recv_th_obj.start()

        if self._output_stdout:
            self._err_th_obj = threading.Thread(target=self._err_th, daemon=True)
            self._err_th_obj.start()

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

    def save_log(self, path: str) -> str:
        """
        保存缓存文件
        :param path:
        :return:
        """
        if not self._is_terminate:
            raise RuntimeError("Can't save log before terminate")

        shutil.copy(self._log_path, path)
        return path

    def save_jou(self, path: str) -> str:
        """
        保存jouarny文件，可直接作为tcl脚本使用
        :param path:
        :return:
        """
        if not self._is_terminate:
            raise RuntimeError("Can't save script before terminate")

        shutil.copy(self._jou_path, path)
        return path

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
                self.save_log(os.path.join(self._save_log, os.path.basename(self._log_path)))
            else:
                raise FileExistsError(f"{self._save_log} is exists")

        if self._clean:
            self.clean_vivado_cache()

    def _err_th(self):
        while self._is_recv:
            s = self.stderr.readline().decode(self._encode)
            if s:
                print("[ERROR]", s)

    def _recv_th(self):
        while self._is_recv:
            try:
                s = self.stdout.readline().decode(self._encode).strip(os.linesep)

                if self._output and s:
                    print("#", s)

                if not self._cur_cmd:
                    continue

                if self._error_check and s.startswith("ERROR"):
                    self._cur_cmd_done.set()
                    self._cur_err = VivadoError.from_str(s)

                ret = re.findall(r"^\[Tcl (end|run)]\s?.*", s)
                if ret:
                    ret = ret[0]
                    if ret == "run":
                        self._is_cur_out = True

                    elif ret == "end":
                        self._is_cur_out = False
                        self._cur_cmd = None
                        self._cur_cmd_done.set()

                elif self._is_cur_out and s:
                    self._cur_out.append(s)

            except Exception as e:
                print(e)
                print(traceback.format_exc())
                raise e

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
        if not tcl.endswith(os.linesep):
            tcl += os.linesep
        try:
            self.stdin.write(tcl.encode())
            self.stdin.flush()
        except OSError as e:
            print("OSError", tcl)
            raise e

    def _send_cmd(self, tcl: str, raw: bool = False) -> None:
        """
        发送tcl语句
        注：
            由于很多 vivado 里 tcl 命令的返回值并没有通过stdout返回，导致了可以在
            vivado 的 tcl 控制台可以看到输出，但是并不会没有输出到 stdout 里。因
            此所以这里对一些的 tcl 语句进行了 puts 处理，使其输出到 stdout 里。
        :param tcl:
        :param raw: 是否优化输出
            True: 绝对不添加 puts 优化输出
            False: 添加 puts 优化输出
        :return:
        """
        tcl_type = tcl.split()[0]

        self._cur_cmd_done.clear()
        self._cur_cmd = tcl
        escape_tcl = self._escape_tcl(self._cur_cmd)

        self._write_2_stdin(f'puts "\[Tcl run\] {escape_tcl}"')

        if raw or (tcl_type in DontDoPutsCmd):
            self._write_2_stdin(tcl)
        else:
            self._write_2_stdin(f'puts [{tcl}]')

        self._write_2_stdin(f'puts "\[Tcl end\]"')

    def run(self, tcl, raw: bool = False) -> list:
        """
        阻塞方式运行tcl语句，完成后返回输出的信息列表
        :param tcl:
            可以是多行的 tcl 语句通过 \n 拼接的，这是 puts优化只会识别检测第一个命令
        :param raw: 是否优化输出
            True: 绝对不添加 puts 优化输出
            False: 添加 puts 优化输出
        :return:
        """
        if self._is_terminate:
            raise ValueError("Tcl process has terminate")

        tcl = tcl.strip(" ").strip("\n")
        if not tcl:
            raise ValueError("tcl can't be empty")

        self._lock.acquire()

        self._send_cmd(tcl, raw=raw)
        self._cur_cmd_done.wait()

        output, self._cur_out = self._cur_out, []
        self._lock.release()

        if self._cur_err:
            raise self._cur_err

        return output
