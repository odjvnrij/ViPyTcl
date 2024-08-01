from typing import Tuple, List
from enum import Enum
from .vivado_error import *

class RunsType(Enum):
    NoneType = ""
    SYNTH = "synthesis"
    IMPL = "implementation"
    SIM = "simulation"

    def __str__(self):
        return self.value


class SimMode(Enum):
    Behavioral = "behavioral"
    PostSynthesis = "post-synthesis"
    PostImplementation = "post-implementation"


class SimType(Enum):
    Functional = "functional"
    Timing = "timing"


CommonPropertyType = {
    "int": int,
    "float": float,
    "string": str,
    "bool": bool,
}


def tcl_args_parse(*args, **kwargs):
    s = " "
    s += "".join((f" {k}" if isinstance(k, ViObj) else f" {{{k}}}" for k in args)) if args else ""
    for k, v in kwargs.items():
        if isinstance(v, bool):
            s += f" -{k}" if v else ""
        elif isinstance(v, (int, float, ViObj)):
            s += f" -{k} {v}"
        else:
            s += f" -{k} {{{v}}}"
    return s


class ViObj:
    """ future feature"""

    def __init__(self, tcl_popen, tcl: str, name: str, **kwargs):
        self._tcl_popen = tcl_popen
        self.tcl = tcl
        self.name = name
        self._kwargs = kwargs

    def __str__(self):
        return f"[{self.tcl} {{{self.name}}}]"

    def __call__(self, *args, **kwargs):
        kwargs.update(self._kwargs)
        s = tcl_args_parse(*args, **kwargs)
        return self._tcl_popen.tcl("%s {%s} %s" % (self.tcl, self.name, s))

    def is_property_read_only(self, name: str):
        result = self._tcl_popen.tcl(f"get_property {self} {{{name}}}")[1:]
        if not result:
            return None

        if result[2] == "true":
            return True
        elif result[2] == "false":
            return False
        else:
            return None

    def get_property_type(self, name: str):
        result = self._tcl_popen.tcl(f"get_property {self} {{{name}}}")[1:]
        if not result:
            return None

        value_type = CommonPropertyType.get(result[1], None)
        return value_type

    def get_property(self, name: str):
        result = self._tcl_popen.tcl(f"get_property {self} {{{name}}}")[1:]
        if not result:
            return ''

        t = result[0].split()  # t: [name, type, read_only, value]
        if len(t) < 4:
            return ''
        else:
            value = t[-1]
            value_type = t[1]
            if value_type == "bool":
                return bool(str(value))
            elif value_type == "int":
                return int(value)
            else:
                return value

    def set_property(self, name=None, value=None, dic=None):
        if not name and not dic:
            raise ViArgsError("name and dic cant be None at same time")
        if name:
            tcl = f"set_property {{{name}}}"
            if isinstance(value, bool):
                tcl += f"set_property {{{name}}} {'{true}' if value else '{false}'}"
            else:
                tcl += f"set_property {{{name}}} {{{value}}}"
        else:
            tcl = f"set_property -dict " + " ".join(("{%s} {%s}" % (k, v) for k, v in dic.item()))
        tcl += f" {self}"
        return self._tcl_popen.tcl(tcl)


class ViObjList:

    def __init__(self, objs: List[ViObj] or Tuple[ViObj]):
        """
        objs 必须存放同类型的ViObj实例
        例如 A 是 ViObjCell 实例 "[get_cells {A}]"
        B 是 ViObjCell 实例 "[get_cells {B}]"
        ViList(A, B) 会返回 ViObjCell实例 "[get_cells {A B}]"
        """
        self._type = objs[0].__class__
        self.tcl = objs[0].tcl
        self._objs = objs.copy()

    def __iter__(self):
        return iter(self._objs)

    def __repr__(self):
        return f"[{self.tcl} {' '.join(obj.name for obj in self._objs)}]"

    def __append__(self, obj: ViObj):
        if not isinstance(obj, self._type):
            raise ViArgsError("obj must be same type with objs")
        self._objs.append(obj)

    def __getitem__(self, item):
        return self._objs[item]


class ViObjRun(ViObj):
    def __init__(self, tcl_popen, run_name: str):
        super().__init__(tcl_popen, f"get_runs", run_name)

    def get_run_type(self):
        result = self()
        if not result:
            raise ViUnexpectedEmptyTclReturnError

        if "WARNING: [Vivado 12-821]" in result[0]:
            return RunsType.NoneType

        is_synth = int(self._tcl_popen.tcl(f"get_property IS_SYNTHESIS [{self}]")[0])
        is_impl = int(self._tcl_popen.tcl(f"get_property IS_IMPLEMENTATION [{self}]")[0])
        if is_synth:
            return RunsType.SYNTH
        elif is_impl:
            return RunsType.IMPL
        else:
            return RunsType.NoneType


class ViObjDesign(ViObj):
    def __init__(self, tcl_popen, design_name: str):
        super().__init__(tcl_popen, "get_designs", design_name)

    def get_design_type(self):
        result = self()
        if not result:
            raise ViUnexpectedEmptyTclReturnError

        if "WARNING: [Vivado 12-628]" in result[0]:
            return RunsType.NoneType

        is_synth = int(self._tcl_popen.tcl(f"get_property IS_SYNTHESIS [get_runs {self.name}]")[0])
        is_impl = int(self._tcl_popen.tcl(f"get_property IS_IMPLEMENTATION [get_runs {self.name}]")[0])
        if is_synth:
            return RunsType.SYNTH
        elif is_impl:
            return RunsType.IMPL
        else:
            return RunsType.NoneType


class ViObjFileset(ViObj):
    def __init__(self, tcl_popen, fileset_name: str):
        super().__init__(tcl_popen, f"get_fileset", fileset_name)

    def get_fileset_type(self):
        return self.get_property("FILESET_TYPE")


class ViObjConstrs(ViObjFileset):
    pass


class ViObjSimset(ViObjFileset):
    pass


class ViObjCell(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, f"get_cells", name)

    def get_type(self):
        return self.get_property("TYPE")

    def get_bel(self):
        return ViObjBel(self._tcl_popen, self.get_property("BEL"))

    def get_site(self):
        return ViObjSite(self._tcl_popen, self.get_property("SITE"))

    def get_tile(self):
        return ViObjTile(self._tcl_popen, self.get_property("TILE"))


class ViObjBel(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, f"get_bels", name)


class ViObjSite(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, f"get_sites", name)


class ViObjTile(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, f"get_tiles", name)


class ViObjPin(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, f"get_pins", name)


class ViObjPort(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, "get_ports", name)


class ViObjHWServer(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, "get_hw_server", name)
        self.ip, self.port = name.split(":")


class ViObjHWDevice(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, "get_hw_device", name)


class ViObjHWTarget(ViObj):
    def __init__(self, tcl_popen, name: str):
        super().__init__(tcl_popen, "get_hw_target", name)
