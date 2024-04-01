import multiprocessing
import os

from base import *


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


class VivadoPrj:
    def __init__(self,
                 prj_path: str,
                 bat_path: str = "",
                 output: bool = True,
                 error_check: bool = True,
                 max_core: int = multiprocessing.cpu_count(), **kwargs):

        self.prj_path = prj_path
        if not self.prj_path.endswith(".xpr"):
            raise FileNotFoundError(f"prj path {prj_path} must end with .xpr")
        if not os.path.exists(prj_path):
            raise FileNotFoundError(f"prj path not exist {prj_path}")

        self.bat_path = bat_path if bat_path else find_vivado_bat()

        self._tcl_proc = TclProcessPopen(self.bat_path, output=output, error_check=error_check, **kwargs)
        self._is_exit = False

        if max_core > multiprocessing.cpu_count():
            self._max_core = multiprocessing.cpu_count()
        else:
            self._max_core = max_core

        self.tcl("open_project " + self.prj_path.replace("\\", "/"))

    def exit(self):
        self.tcl("exit")
        self._tcl_proc.terminate()
        self._is_exit = True

    def tcl(self, tcl_cmd: str):
        if self._is_exit:
            raise ViTclCantRunError("vivado is exit, can't run tcl cmd")
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

    def save_prj(self):
        self.tcl("save_project")

    def close_prj(self, save: bool = True):
        if save:
            self.tcl("close_project -save true")
        else:
            self.tcl("close_project -save false")

    def _common_get(self, cmd: str,
                    pattern: str = "*",
                    regexp: bool = False,
                    filter_: Filter = None or str,
                    of_objects: str or ViObj = "", **kwargs) -> List[str]:

        tcl = f"{cmd} {{{pattern}}}"
        tcl += f" -filter {{{filter_}}}" if filter_ else ""
        tcl += f" -of_objects {of_objects}" if of_objects else ""
        tcl += " -regexp" if regexp else ""
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)
        if not result:
            return []
        elif "WARNING: [Vivado" in result[0]:
            return []
        else:
            return result[0].split()

    """ ============================ runs =========================== """

    def get_designs(self,
                    pattern: str = "*",
                    regexp: bool = False,
                    filter_: Filter = None or str,
                    of_objects: str or ViObj = "", **kwargs) -> List[str]:
        return self._common_get("get_designs", pattern, regexp, filter_, of_objects, **kwargs)

    def current_design(self, *args, **kwargs) -> List[str]:
        result = self.tcl("current_design" + tcl_args_parse(*args, **kwargs))
        return result[0].split()

    def close_design(self, *args, **kwargs) -> List[str]:
        return self.tcl("close_design" + tcl_args_parse(*args, **kwargs))

    """ ============================ runs =========================== """

    def get_runs(self,
                 pattern: str = "*",
                 regexp: bool = False,
                 filter_: Filter = None or str,
                 of_objects: str or ViObj = "", **kwargs) -> Tuple[ViObjRun, ...]:
        runs = self._common_get("get_runs", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjRun(self._tcl_proc, run) for run in runs)

    def open_run(self, run: str or ViObjRun, **kwargs) -> ViObjRun:
        name = kwargs.pop("name") if "name" in kwargs else run
        result = self.tcl(f"open_run {run} -name {name}" + tcl_args_parse(**kwargs))
        if result[-1] != run:
            raise ViRunNameDontMatch
        return ViObjRun(self._tcl_proc, run)

    def create_run(self, run: str, flow: str, constrs: str or ViObjConstrs = "", **kwargs) -> ViObjRun:
        """ kwargs 里如果有 -quiet 或者 -q 等参数，tcl会返回空列表 """
        kwargs["constrs"] = constrs
        tcl = f"create_run {run} -flow {{{flow}}}" + tcl_args_parse(**kwargs)

        result = self.tcl(tcl)
        if result and result[-1] != run:
            raise ViRunNameDontMatch

        return ViObjRun(self._tcl_proc, run)

    def reset_runs(self, run: str or ViObjRun, **kwargs) -> List[str]:
        return self.tcl(f"reset_run {run}" + tcl_args_parse(**kwargs))

    def wait_on_run(self, run: str or ViObjRun, timeout: int = 1, **kwargs) -> List[str]:
        return self.tcl(f"wait_on_run {run} -timeout {timeout}" + tcl_args_parse(**kwargs))

    def launch_runs(self, run: str or ViObjRun, force: bool = False, **kwargs) -> List[str]:
        if force:
            return self.tcl(f"launch_runs {run} -force" + tcl_args_parse(**kwargs))
        else:
            return self.tcl(f"launch_runs {run}" + tcl_args_parse(**kwargs))

    def get_runs_type(self, run: str or ViObjRun) -> RunsType:
        return self.get_runs(run)[0].get_run_type()

    def current_run(self, run: str or ViObjRun = "", synth: bool = False, impl: bool = False, **kwargs) -> List[str]:
        """ 当传入 run 即为将该 run 对应的 synth 和 impl 设置为 active """
        if synth and impl:
            raise ViArgsError("synth and impl cant be set True at same time")

        tcl = f"current_run {run}"
        if synth:
            tcl += "-s"
        elif impl:
            tcl += "-i"
        tcl += tcl_args_parse(**kwargs)
        return self.tcl(tcl)

    """ ============================ fileset =========================== """

    def create_fileset(self, fileset_name: str, constrs: str or ViObjConstrs = "", *args, **kwargs) -> ViObjFileset:
        tcl = f"create_fileset {fileset_name} -constrset {constrs}" + tcl_args_parse(*args, **kwargs)
        self.tcl(tcl)
        return ViObjFileset(self._tcl_proc, fileset_name)

    def get_filesets(self,
                     pattern: str = "*",
                     regexp: bool = False,
                     filter_: Filter = None or str,
                     of_objects: str or ViObj = "", **kwargs) -> Tuple[ViObjFileset, ...]:
        filesets = self._common_get("get_filesets", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjFileset(self._tcl_proc, fileset) for fileset in filesets)

    def current_fileset(self, *args, **kwargs) -> ViObjFileset:
        result = self.tcl("current_fileset" + tcl_args_parse(*args, **kwargs))
        fileset = result[0]
        return ViObjFileset(self._tcl_proc, fileset)

    def current_constrs(self, *args, **kwargs) -> ViObjFileset:
        result = self.tcl("current_fileset -c" + tcl_args_parse(*args, **kwargs))
        fileset = result[0]
        return ViObjFileset(self._tcl_proc, fileset)

    def delete_fileset(self, *args, **kwargs) -> List[str]:
        return self.tcl("delete_fileset" + tcl_args_parse(*args, **kwargs))

    """ ============================ file =========================== """

    def add_files(self, file_path: str or Tuple or List, fileset: str or ViObjFileset = "", norecurse: bool = False,
                  copy_to: str = "", force: bool = False, **kwargs) -> List[str]:
        if fileset:
            tcl = f"add_files -fileset {fileset}"
        else:
            tcl = f"add_files"

        if isinstance(file_path, str):
            tcl += " {%s}" % file_path
        else:
            tcl += " {%s}" % " ".join(file_path)

        tcl += " -norecurse" if norecurse else ""
        tcl += f" -copy_to {{{copy_to}}}" if copy_to else ""
        tcl += " -force" if force else ""
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return self.tcl(tcl)

    def get_files(self,
                  patterns: str = "*",
                  regexp: bool = False,
                  filter_: Filter = None or str,
                  of_objects: str or ViObj = "",
                  used_in: RunsType = None,
                  all_: bool = False, **kwargs
                  ) -> List[str]:
        if used_in and used_in is not RunsType.NoneType:
            kwargs["used_in"] = used_in
        kwargs["all"] = all_
        return self._common_get("get_files", patterns, regexp, filter_, of_objects, **kwargs)

    def remove_files(self, files: str or List or Tuple, fileset: ViObjFileset or str = "", **kwargs) -> List[str]:
        if fileset:
            tcl = f"remove_files -fileset {fileset} {{{files}}}"
        else:
            tcl = f"remove_files {{{files}}}"

        if isinstance(files, str):
            files = [files]
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        tcl += " ".join(files)
        return self.tcl(tcl)

    """ ============================ cells =========================== """

    def get_cells(self,
                  pattern: str = "*",
                  regexp: bool = False,
                  filter_: Filter = None or str,
                  of_objects: str or ViObj = "",
                  hierarchy: bool = False,
                  nocase: bool = False,
                  include_replicated_objects: bool = False,
                  hsc: str = "",
                  **kwargs) -> Tuple[ViObjCell]:
        kwargs["hierarchy"] = hierarchy
        kwargs["nocase"] = nocase
        kwargs["include_replicated_objects"] = include_replicated_objects
        if hsc:
            kwargs["hsc"] = hsc
        cells = self._common_get("get_cells", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjCell(self._tcl_proc, cell) for cell in cells)

    def unplace_cells(self, cells: str or List[ViObjCell], **kwargs) -> List[str]:
        """ cells 传入list或tuple时，内部元素必须要么全部是str，要么全是ViObjCell """
        if isinstance(cells, str):
            cells_list = ViObjCell(self._tcl_proc, cells)
        else:
            if isinstance(cells[0], ViObjCell):
                cells_list = ViObjList(cells)
            else:
                cells_list = ViObjCell(self._tcl_proc, " ".join(cells))

        tcl = f"unplace_cells {cells_list}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return self.tcl(tcl)

    def rename_cell(self, from_cell: str or ViObjCell, to_cell: str, **kwargs) -> ViObjCell:
        if isinstance(from_cell, ViObjCell):
            tcl = f"rename_cell {from_cell} -to {{{to_cell}}}"
        else:
            tcl = f"rename_cell {{{from_cell}}} -to {{{to_cell}}}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return ViObjCell(self._tcl_proc, to_cell)

    def remove_cell(self, cells: str or List[ViObjCell], **kwargs) -> List[str]:
        if isinstance(cells, str):
            cells_list = ViObjCell(self._tcl_proc, cells)
        else:
            if isinstance(cells[0], ViObjCell):
                cells_list = ViObjList(cells)
            else:
                cells_list = ViObjCell(self._tcl_proc, " ".join(cells))

        tcl = f"remove_cell {cells_list}"
        tcl += tcl_args_parse(kwargs) if kwargs else ""
        return self.tcl(tcl)

    def place_cell(self,
                   cell: str or ViObjCell = "",
                   bel: str or ViObjBel = "",
                   cell_bel_pair: List[Tuple[ViObjCell, ViObjBel]] = None, **kwargs) -> List[str]:
        if not any((cell, bel, cell_bel_pair)):
            raise ViArgsError("cell, bel, cell_bel_pair cant be all None")

        if cell and bel:
            tcl = f"place_cell {cell} {bel}"
        else:
            tcl = "place_cell"
            tcl += " {%s}" % (" ".join(f"{c} {b}" for c, b in cell_bel_pair))

        tcl += tcl_args_parse(**kwargs)
        return self.tcl(tcl)

    """ ============================ bel =========================== """

    """ ============================ site =========================== """

    """ ============================ tile =========================== """

    """ ============================ pins =========================== """
