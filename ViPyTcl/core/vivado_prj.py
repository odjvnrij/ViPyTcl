import multiprocessing
import os

from .global_var import DefaultVivadoBatPath
from ..base import *
from .tcl_process import *


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

        self.bat_path = bat_path if bat_path else DefaultVivadoBatPath

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

    def current_design(self, design: str or ViObjDesign = "", **kwargs) -> ViObjDesign or None:
        tcl = f"current_design {design}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)[0]

        if "WARNING: " in result:
            return None
        return ViObjDesign(self._tcl_proc, result)

    def close_design(self, design: str or ViObjDesign = "", **kwargs) -> List[str]:
        tcl = f"close_design {design}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return self.tcl(tcl)

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

    def current_fileset(self, fileset: str or ViObjFileset = "", **kwargs) -> ViObjFileset or None:
        tcl = f"current_fileset {fileset}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)
        fileset = result[0]
        if "WARNNING: " in fileset:
            return None
        return ViObjFileset(self._tcl_proc, fileset)

    def current_constrs(self, fileset: str or ViObjFileset = "", **kwargs) -> ViObjFileset or None:
        tcl = f"current_fileset {fileset} -c"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)
        fileset = result[0]
        if "WARNNING: " in fileset:
            return None
        return ViObjFileset(self._tcl_proc, fileset)

    def current_simset(self, fileset: str or ViObjFileset = "", **kwargs) -> ViObjSimset or None:
        tcl = f"current_fileset {fileset} -s"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)
        fileset = result[0]
        if "WARNNING: " in fileset:
            return None
        return ViObjSimset(self._tcl_proc, fileset)

    def delete_fileset(self, fileset: str or ViObjFileset = "", **kwargs) -> List[str]:
        tcl = f"delete_fileset {fileset}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return self.tcl(tcl)

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

    def get_bels(self,
                 pattern: str = "*",
                 regexp: bool = False,
                 filter_: Filter = None or str,
                 of_objects: str or ViObj = "",
                 **kwargs) -> Tuple[ViObjBel, ...]:
        bels = self._common_get("get_bels", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjBel(self._tcl_proc, bel) for bel in bels)

    def get_bel_pins(self,
                     pattern: str = "*",
                     regexp: bool = False,
                     filter_: Filter = None or str,
                     of_objects: str or ViObjBel = "",
                     **kwargs) -> Tuple[ViObjPin, ...]:
        pins = self._common_get("get_bel_pins", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjPin(self._tcl_proc, pin) for pin in pins)

    """ ============================ site =========================== """

    def get_sites(self,
                  pattern: str = "*",
                  regexp: bool = False,
                  filter_: Filter = None or str,
                  of_objects: str or ViObj = "",
                  **kwargs) -> Tuple[ViObjSite, ...]:
        sites = self._common_get("get_sites", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjSite(self._tcl_proc, site) for site in sites)

    def get_site_pins(self,
                      pattern: str = "*",
                      regexp: bool = False,
                      filter_: Filter = None or str,
                      of_objects: str or ViObjBel = "",
                      **kwargs) -> Tuple[ViObjPin, ...]:
        pins = self._common_get("get_site_pins", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjPin(self._tcl_proc, pin) for pin in pins)

    """ ============================ tile =========================== """

    def get_tiles(self,
                  pattern: str = "*",
                  regexp: bool = False,
                  filter_: Filter = None or str,
                  of_objects: str or ViObj = "",
                  **kwargs) -> Tuple[ViObjTile, ...]:
        tiles = self._common_get("get_tiles", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjTile(self._tcl_proc, tile) for tile in tiles)

    """ ============================ pins =========================== """

    def get_pins(self,
                 pattern: str = "*",
                 regexp: bool = False,
                 filter_: Filter = None or str,
                 of_objects: str or ViObj = "",
                 **kwargs) -> Tuple[ViObjPin, ...]:
        pins = self._common_get("get_pins", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjPin(self._tcl_proc, pin) for pin in pins)

    def rename_pin(self, from_pin: str or ViObjPin, to_pin: str, **kwargs) -> ViObjPin:
        if isinstance(from_pin, ViObjPin):
            tcl = f"rename_pin {from_pin} -to {{{to_pin}}}"
        else:
            tcl = f"rename_pin {from_pin} -to {{{to_pin}}}"

        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return ViObjPin(self._tcl_proc, to_pin)

    def remove_pin(self, pins: str or List[ViObjPin], **kwargs) -> List[str]:
        if isinstance(pins, str):
            cells_list = ViObjPin(self._tcl_proc, pins)
        else:
            if isinstance(pins[0], ViObjCell):
                cells_list = ViObjList(pins)
            else:
                cells_list = ViObjPin(self._tcl_proc, " ".join(pins))

        tcl = f"remove_pin {cells_list}"
        tcl += tcl_args_parse(kwargs) if kwargs else ""
        return self.tcl(tcl)

    """ ============================ ports =========================== """

    def get_ports(self,
                  pattern: str = "*",
                  regexp: bool = False,
                  filter_: Filter = None or str,
                  of_objects: str or ViObj = "",
                  **kwargs) -> Tuple[ViObjPort, ...]:
        ports = self._common_get("get_ports", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjPort(self._tcl_proc, port) for port in ports)

    def rename_port(self, from_port: str or ViObjPort, to_port: str, **kwargs) -> ViObjPort:
        if isinstance(from_port, ViObjPort):
            tcl = f"rename_port {from_port} -to {{{to_port}}}"
        else:
            tcl = f"rename_port {{{from_port}}} -to {{{to_port}}}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return ViObjPort(self._tcl_proc, to_port)

    def remove_port(self, ports: str or List[ViObjPort], **kwargs) -> List[str]:
        if isinstance(ports, str):
            ports_list = ViObjPort(self._tcl_proc, ports)
        else:
            if isinstance(ports[0], ViObjPort):
                ports_list = ViObjList(ports)
            else:
                ports_list = ViObjPort(self._tcl_proc, " ".join(ports))

        tcl = f"remove_port {ports_list}"
        tcl += tcl_args_parse(kwargs) if kwargs else ""
        return self.tcl(tcl)

    """ ================= hw ================="""
    "connect_hw_server"

    def open_hw_manager(self, **kwargs) -> List[str]:
        return self.tcl("open_hw_manager" + tcl_args_parse(**kwargs) if kwargs else "")

    def close_hw_manager(self, **kwargs) -> List[str]:
        return self.tcl("close_hw_manager" + tcl_args_parse(**kwargs) if kwargs else "")

    def get_hw_server(self,
                      pattern: str = "*",
                      regexp: bool = False,
                      filter_: Filter = None or str,
                      of_objects: str or ViObj = "",
                      **kwargs) -> Tuple[ViObjHWServer, ...]:
        servers = self._common_get("get_hw_server", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjHWServer(self._tcl_proc, server) for server in servers)

    def current_hw_server(self, hw_server: str or ViObjHWServer, **kwargs) -> ViObjHWServer or None:
        tcl = f"current_hw_server {hw_server}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)[0]

        if "WARNING: [Labtoolstcl 44-29]" in result:
            return None
        return ViObjHWServer(self._tcl_proc, result)

    def connect_hw_server(self, url: str or ViObjHWServer, **kwargs) -> List[str]:
        tcl = f"connect_hw_server {url}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return self.tcl(tcl)

    def disconnect_hw_server(self, url: str or ViObjHWServer, **kwargs) -> List[str]:
        if isinstance(url, ViObjHWServer):
            tcl = f"disconnect_hw_server {url}"
        else:
            tcl = f"disconnect_hw_server {{{url}}}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return self.tcl(tcl)

    def refresh_hw_server(self, url: str or ViObjHWServer, force_poll: bool = False, **kwargs) -> List[str]:
        tcl = f"refresh_hw_server {url}"
        tcl += " -force_poll" if force_poll else ""
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        return self.tcl(tcl)

    def get_hw_devices(self,
                       pattern: str = "*",
                       regexp: bool = False,
                       filter_: Filter = None or str,
                       of_objects: str or ViObj = "",
                       **kwargs) -> Tuple[ViObjHWDevice, ...]:
        devs = self._common_get("get_hw_server", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjHWDevice(self._tcl_proc, dev) for dev in devs)

    def current_hw_device(self, dev: str or ViObjHWDevice, **kwargs) -> ViObjHWDevice or None:
        tcl = f"current_hw_device {dev}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)[0]
        if "WARNING: " in result[0]:
            return None
        return ViObjHWDevice(self._tcl_proc, result)

    def create_hw_target(self, hw_target_name: str, copy: str or ViObjHWTarget, **kwargs) -> ViObjHWTarget:
        tcl = f"create_hw_target {{{hw_target_name}}}"
        if isinstance(copy, ViObjHWTarget):
            tcl += f" -copy {copy}"
        else:
            tcl += f" -copy {{{copy}}}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        self.tcl(tcl)
        return ViObjHWTarget(self._tcl_proc, hw_target_name)

    def get_hw_target(self,
                      pattern: str = "*",
                      regexp: bool = False,
                      filter_: Filter = None or str,
                      of_objects: str or ViObj = "",
                      **kwargs) -> Tuple[ViObjHWTarget, ...]:
        tars = self._common_get("get_hw_target", pattern, regexp, filter_, of_objects, **kwargs)
        return tuple(ViObjHWTarget(self._tcl_proc, tar) for tar in tars)

    def current_hw_target(self, tar: str or ViObjHWTarget, **kwargs) -> List or Tuple[ViObjHWTarget] or None:
        tcl = f"get_hw_target {tar}"
        tcl += tcl_args_parse(**kwargs) if kwargs else ""
        result = self.tcl(tcl)[0]

        if "WARNING: [" in result[0]:
            return []
        return ViObjHWTarget(self._tcl_proc, result)

    """ ================= bitstream ================="""

    def write_bits(self, bit_path: str, force: bool = False) -> List[str]:
        if self.current_design().get_design_type() is not RunsType.IMPL:
            raise ViNotInRightDesign("write bitstream must be in impl design")

        os.makedirs(bit_path, exist_ok=True)
        bit_path = bit_path.replace("\\", "/")
        tcl = f"write_bitstream -force {bit_path}" if force else f"write_bitstream {bit_path}"
        return self.tcl(tcl)

    def program_bits(self, bit_path: str) -> List[str]:
        if not os.path.exists(bit_path):
            raise FileNotFoundError(f"bit file not found: {bit_path}")

        bit_path = bit_path.replace("\\", "/")
        return self.tcls("open_hw_manager",
                         "connect_hw_server",
                         "open_hw_target",
                         "current_hw_device [lindex [get_hw_devices] 0]",
                         "refresh_hw_device -update_hw_probes false [current_hw_device]",
                         f"set_property PROGRAM.FILE {bit_path} [current_hw_device]",
                         "program_hw_devices [current_hw_device]",
                         "close_hw_manager"
                         )
