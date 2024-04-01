import multiprocessing
import os

from .vivado_const import *
from base.base import *


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


def _runs_exist_check(func):
    def inner(*args, **kwargs):
        run_name = args[1]
        if run_name and not args[0].is_run_exist(run_name):
            raise ViRunNotExist(f"run {run_name} not exist")
        return func(*args, **kwargs)

    return inner


class BaseVivadoPrjWithTcl:

    def __init__(self,
                 bat_path: str = "",
                 output: bool = True,
                 error_check: bool = True,
                 max_core: int = multiprocessing.cpu_count(), **kwargs):

        self.bat_path = bat_path if bat_path else find_vivado_bat()
        self._tcl_proc = TclProcessPopen(self.bat_path, output=output, error_check=error_check, **kwargs)
        self._is_exit = False

        self._cur_prj = None
        self._cur_design_type = RunsType.NoneType
        self._cur_design = ""

        if max_core > multiprocessing.cpu_count():
            self._max_core = multiprocessing.cpu_count()
        else:
            self._max_core = max_core

    def exit(self):
        self.tcl("exit")
        self._tcl_proc.terminate()
        self._is_exit = True

    def tcl(self, tcl_cmd: str):
        if self._is_exit:
            raise ViTclCantRunError("vivado is exit, can't run tcl cmd")
        elif not self._cur_prj and not tcl_cmd.startswith("open_project"):
            raise ViNoPrjFoundError("must open prj first")
        return self._tcl_proc.run(tcl_cmd)

    def tcls(self, *tcl_cmds):
        tcl_cmd = "\n".join(tcl_cmds)
        return self.tcl(tcl_cmd)

    def save_log(self, path: str):
        if not self._is_exit:
            raise ViUnexit("Can't save log before terminate")
        self._tcl_proc.save_log(path)

    def save_script(self, path: str):
        if not self._is_exit:
            raise ViUnexit("Can't save script before terminate")
        self._tcl_proc.save_jou(path)

    def exec_script(self, tcl_path: str):
        tcl_path = tcl_path.replace("\\", "/")
        if not os.path.exists(tcl_path):
            raise FileNotFoundError(f"tcl script dont exist {tcl_path}")

        self.tcl(f"source {tcl_path}")

    def save_constrs(self, force: bool = True):
        self.tcl("save_constraints -force") if force else self.tcl("save_constraints")

    """ ================= project ================="""

    def open_prj(self, prj_path: str):
        prj_path = prj_path.replace("\\", "/")
        if not os.path.exists(prj_path):
            raise FileNotFoundError(f"prj path dont exist {prj_path}")

        self.tcl(f"open_project {prj_path}")

        self._cur_prj = prj_path
        self.tcl(f"update_compile_order -fileset [{CurFileset}]")

    def save_prj(self):
        self.tcl("save_project")

    def close_prj(self, save: bool = True):
        if save:
            self.tcl("close_project -save true")
        else:
            self.tcl("close_project -save false")

    """ ================= design ================="""

    def close_design(self, design_name: str, quiet: bool = True):
        tcl = f"close_design {design_name}"
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    def switch_design(self, design_name: str, quiet: bool = False) -> List[str]:
        return self.current_design(design_name, quiet)

    def get_design(self, design_name: str = "", regexp: bool = False, filter_str: str = "", quiet: bool = True,
                   no_case: bool = False) -> List[str]:
        tcl = f"get_design {design_name}"
        tcl += " -regexp" if regexp else ""
        tcl += f" -filter {{{filter_str}}}" if filter_str else ""
        tcl += " -q" if quiet else ""
        tcl += " -nocase" if no_case else ""
        return self.tcl(tcl)

    def current_design(self, design_name: str = "", quiet: bool = False) -> List[str]:
        tcl = f"current_design {design_name}"
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    def get_cur_design_type(self) -> RunsType:
        return self.get_runs_type("[current_design]")

    def refresh_design(self, quiet: bool = True) -> List[str]:
        tcl = "refresh_design"
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    """ ================= run ================="""

    def current_run(self, run_name: str = "", synth: bool = False, impl: bool = False,
                    quiet: bool = False) -> List[str]:
        """ 注：
            慎用current_run，current_run的返回不可以用作一些状态的描述
            因为 current_run 指的是当前设置了 active 状态的 runs
            -s 和 -i 也只是返回当前 active 下的 synth 或者 impl
            但是如果传入了 run_name，意味着要设置 run_name 为 active
        """
        if synth and impl:
            raise ViArgsError("synth and impl can't be True at the same time")
        tcl = f"current_run {run_name}"
        if synth:
            tcl += " -s"
        elif impl:
            tcl += " -i"
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    def get_runs(self, run_name: str = "", regexp: bool = False, filter_str: str = "", quiet: bool = True,
                 no_case: bool = False) -> List[str]:
        tcl = f"get_runs {run_name}"
        tcl += " -regexp" if regexp else ""
        tcl += f" -filter {{{filter_str}}}" if filter_str else ""
        tcl += " -q" if quiet else ""
        tcl += " -nocase" if no_case else ""
        return self.tcl(tcl)

    def is_run_exist(self, run_name: str):
        """
        检查runs是否存在
        :param run_name:
        :return:
        """
        runs = self.tcl(TclGetRuns(run_name))
        if "[Vivado 12-821]" in runs[0]:
            return False
        return True

    @_runs_exist_check
    def open_run(self, run_name: str, quiet: bool = False) -> List[str]:
        """
        每个 run 经过 open_run 之后，就会变成 design，design名字由 open_run 时传递的参数 -name <name> 决定
        由于这个原因， open_run 时如果没有指定 -name，就会返回给你一个默认的 design 名字，类似 design_1。该名字
        可以通过get_design获取，但是仍旧比较难获得 design 名字和 run 名字之间的关系。因此在 open_run 时，默认传
        入 -name 为 run_name，这样可以保证 design 名字和 run 名字一致，方便后续操作
        """
        tcl = f"open_run {run_name} -name {run_name}"
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    open_runs = open_run

    @_runs_exist_check
    def reset_runs(self, run_name: str, prev_step: bool = False, from_step: str = "", quiet: bool = False):
        tcl = f"reset_runs {run_name}"
        tcl += " -prev_step" if prev_step else ""
        tcl += f" -from_step {{{from_step}}}" if from_step else ""
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    def wait_on_run(self, run_name: str = "", timeout: int = -1, quiet: bool = False):
        if not isinstance(timeout, int):
            raise TypeError("block must be int")

        tcl = f"wait_on_run {run_name}"
        tcl += f" -timeout {timeout}" if timeout else ""
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    @_runs_exist_check
    def launch_runs(self, run_name: str, timeout: int = -1, script_only: bool = False, force: bool = False):

        tcl = f"launch_runs {run_name} -jobs {self._max_core}"
        tcl += " -script_only" if script_only else ""
        tcl += " -force" if force else ""
        result = self.tcl(tcl)

        if timeout == 0:
            return result
        else:
            self.wait_on_run(run_name, timeout)

    @_runs_exist_check
    def get_runs_type(self, run_name: str) -> RunsType:
        """
        Get runs type
        :param run_name:
        :return:
        """
        is_synth = int(self.tcl(f"get_property IS_SYNTHESIS [get_run {run_name}]")[0])
        is_impl = int(self.tcl(f"get_property IS_IMPLEMENTATION [get_run {run_name}]")[0])
        if is_synth:
            return RunsType.SYNTH
        elif is_impl:
            return RunsType.IMPL
        else:
            return RunsType.NoneType

    """ ================= common ================="""

    def current_fileset(self, fileset_name: str = "", constrs: bool = True, quiet: bool = False) -> List[str]:
        tcl = f"current_fileset {fileset_name}"
        tcl += " -constrset" if constrs else ""
        tcl += " -q" if quiet else ""
        return self.tcl(tcl)

    def get_cur_constrs(self) -> List[str]:
        return self.get_property(CurFilesetConstrs, "TARGET_CONSTRS_FILE")

    def get_cur_global_define(self) -> List[str]:
        return self.tcl("get_files -of [%s] -filter {%s}" % (CurFileset, IsGlobalInclude))

    def get_property(self, obj: str, key: str):
        property_list = self.tcl(f"get_property {key} [{obj}]")
        if not property_list:
            raise ViNoSuchProperty(f"the obj {obj} might not have property {key}")
        return property_list

    def report_property(self, obj: str, key: str = "", regexp: bool = False, append: str = "") -> List[tuple]:
        tcl = f"report_property [{obj}] {key}"
        tcl += " -regexp" if regexp else ""
        tcl += f" -append {{{append}}}" if append else ""

        property_list = self.tcl(tcl)
        if not property_list:
            raise ViUnexpectedEmptyTclReturnError

        if len(property_list) == 1:
            return []

        result = []
        for i in property_list[1:]:
            key, value_type, read_only, value = i.split()

            if value_type == "Type":
                value = bool(int(value))

            if read_only == "true":
                read_only = True
            elif read_only == "false":
                read_only = False
            else:
                raise ViUnknownPropertyValue(f"unexpected read_only value {read_only}")

            result.append((key, value, value_type, read_only))
        return result

    """ ================= obj ================="""

    def _get_parts(self, get_parts: str, obj: str = "", of_obj: bool = False, regexp: bool = False,
                   no_case: bool = False,
                   filter_str: str = "", **kwargs) -> List[str]:
        if of_obj and regexp:
            raise ViArgsError("of_obj and regexp can't be True at the same time")

        if of_obj:
            tcl = f"{get_parts} -of_objects [{obj}]"
        else:
            tcl = f"{get_parts} {obj}"
            tcl += " -regexp" if regexp else ""

        tcl += " -nocase" if no_case else ""
        tcl += f" -filter {{{filter_str}}}" if filter_str else ""

        for k, v in kwargs.items():
            if v is False:
                continue
            elif v is True:
                tcl += f" -{k}"
            else:
                tcl += f" -{k} {v}"

        return self.tcl(tcl)

    def get_nets(self, obj: str = "", of_obj: bool = False, regexp: bool = False, no_case: bool = False,
                 filter_str: str = "", include_replicated_objects: bool = False) -> List[str]:
        return self._get_parts("get_nets", obj, of_obj, regexp, no_case, filter_str,
                               include_replicated_objects=include_replicated_objects)

    def get_cells(self, obj: str = "", of_obj: bool = False, regexp: bool = False, no_case: bool = False,
                  filter_str: str = "", include_replicated_objects: bool = False) -> List[str]:
        return self._get_parts("get_cells", obj, of_obj, regexp, no_case, filter_str,
                               include_replicated_objects=include_replicated_objects)

    def get_pins(self, obj: str = "", of_obj: bool = False, regexp: bool = False, no_case: bool = False,
                 filter_str: str = "", include_replicated_objects: bool = False) -> List[str]:
        return self._get_parts("get_pins", obj, of_obj, regexp, no_case, filter_str,
                               include_replicated_objects=include_replicated_objects)

    def get_ports(self, obj: str = "", of_obj: bool = False, regexp: bool = False, no_case: bool = False,
                  filter_str: str = "") -> List[str]:
        return self._get_parts("get_ports", obj, of_obj, regexp, no_case, filter_str)

    """ ================= hw ================="""

    def open_hw(self):
        return self.tcls("open_hw_manager", "connect_hw_server")

    def open_hw_target(self):
        return self.tcl("open_hw_target")

    def get_hw_target(self):
        return self.tcl("get_hw_targets")

    def get_cur_hw_target(self):
        return self.tcl("current_hw_target")

    """ ================= bitstream ================="""

    def write_bits(self, bit_path: str):
        if self.get_cur_design_type() is not RunsType.IMPL:
            raise ViNotInRightDesign("write bitstream must be in impl design")

        os.makedirs(os.path.dirname(bit_path), exist_ok=True)
        bit_path = bit_path.replace("\\", "/")
        self.tcl(f"write_bitstream -force {bit_path}")

    def program_bits(self, bit_path: str):
        if not os.path.exists(bit_path):
            raise FileNotFoundError(f"bit file not found: {bit_path}")

        bit_path = bit_path.replace("\\", "/")
        self.tcls("open_hw_manager",
                  "connect_hw_server",
                  "open_hw_target",
                  "current_hw_device [lindex [get_hw_devices] 0]",
                  "refresh_hw_device -update_hw_probes false [current_hw_device]",
                  f"set_property PROGRAM.FILE {bit_path} [current_hw_device]",
                  "program_hw_devices [current_hw_device]",
                  "close_hw_manager"
                  )


VivadoHM = BaseVivadoPrjWithTcl()
