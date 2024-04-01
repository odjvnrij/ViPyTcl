class Filter:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __and__(self, other: 'Filter' or str):
        return Filter(f"{self} && {other}") if isinstance(other, Filter) else Filter(f"{self} && {{{other}}}")

    def __or__(self, other: 'Filter' or str):
        return Filter(f"{self} || {other}") if isinstance(other, Filter) else Filter(f"{self} || {{{other}}}")

    def __invert__(self):
        return Filter(f"!{self}")

    def __eq__(self, other: 'Filter' or str):
        return Filter(f"{self} == {other}") if isinstance(other, Filter) else Filter(f"{self} == {{{other}}}")

    def __ne__(self, other: 'Filter' or str):
        return Filter(f"{self} !~ {other}") if isinstance(other, Filter) else Filter(f"{self} !~ {{{other}}}")

    def __lt__(self, other: 'Filter' or str):
        return Filter(f"{self} < {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} < {{{other}}}")

    def __le__(self, other: 'Filter' or str):
        return Filter(f"{self} <= {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} <= {{{other}}}")

    def __gt__(self, other: 'Filter' or str):
        return Filter(f"{self} > {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} > {{{other}}}")

    def __ge__(self, other: 'Filter' or str):
        return Filter(f"{self} >= {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} >= {{{other}}}")

    def match(self, pattern: str):
        if not isinstance(pattern, str):
            raise ValueError("filter_obj must be Filter instance")
        return f'{self} =~ "{pattern}"'

    def not_match(self, pattern: str):
        if not isinstance(pattern, str):
            raise ValueError("filter_obj must be Filter instance")
        return f'{self} !~ "{pattern}"'

""" Common filters """
NAME = Filter("NAME")
CLASS = Filter("CLASS")
TYPE = Filter("TYPE")
""" Common filters """

FILE_TYPE = Filter("FILE_TYPE")
FILE_TYPE.Verilog = Filter("Verilog")
FILE_TYPE.VerilogHeader = Filter("VerilogHeader")
FILE_TYPE.VerilogTemplate = Filter("VerlogTemplate")
FILE_TYPE.SystemVerilog = Filter("SystemVerilog")
FILE_TYPE.VHDL = Filter("VHDL")
FILE_TYPE.VHDL2008 = Filter("VHDL2008")
FILE_TYPE.VHDLTemplate = Filter("VHDLTemplate")
FILE_TYPE.EDIF = Filter("EDIF")
FILE_TYPE.XDC = Filter("XDC")
FILE_TYPE.IP = Filter("IP")
FILE_TYPE.TCL = Filter("TCL")
FILE_TYPE.SystemC = Filter("SystemC")
FILE_TYPE.BlockDesign = Filter("BlockDesign")
FILE_TYPE.MemoryInitializationFiles = Filter("MemoryInitializationFiles")

USED_IN_IMPLEMENTATION = Filter("USED_IN_IMPLEMENTATION")
USED_IN_SYNTHESIS = Filter("USED_IN_SYNTHESIS")
USED_IN_SIMULATION = Filter("USED_IN_SIMULATION")

IS_ENABLED = Filter("IS_ENABLED")
IS_AVAILABLE = Filter("IS_AVAILABLE")
IS_GENERATED = Filter("IS_GENERATED")
IS_GLOBAL_INCLUDE = Filter("IS_GLOBAL_INCLUDE")
IS_NGC_WRAPPER = Filter("IS_NGC_WRAPPER")

DRIVER_COUNT = Filter("DRIVER_COUNT")
FLAT_PIN_COUNT = Filter("FLAT_PIN_COUNT")
IS_CONTAIN_ROUTING = Filter("IS_CONTAIN_ROUTING")
IS_INTERNAL = Filter("IS_INTERNAL")
IS_REUSED = Filter("IS_REUSED")
IS_ROUTE_FIXED = Filter("IS_ROUTE_FIXED")
MARK_DEBUG = Filter("MARK_DEBUG")
PARENT = Filter("PARENT")
PIN_COUNT = Filter("PIN_COUNT")

ROUTE_STATUS = Filter("ROUTE_STATUS")
ROUTE_STATUS.UNPLACED = Filter("UNPLACED")
ROUTE_STATUS.INTRASITE = Filter("INTRASITE")

SINK_COUNT = Filter("SINK_COUNT")
SINK_COUNT.SIGNAL = Filter("SIGNAL")

IS_BLACKBOX = Filter("IS_BLACKBOX")
IS_DEBUGGABLE = Filter("IS_DEBUGGABLE")
IS_MATCHED = Filter("IS_MATCHED")
IS_ORIG_CELL = Filter("IS_ORIG_CELL")
IS_PRIMITIVE = Filter("IS_PRIMITIVE")
IS_SEQUENTIAL = Filter("IS_SEQUENTIAL")
LINE_NUMBER = Filter("LINE_NUMBER")
REF_NAME = Filter("REF_NAME")
REF_PIN_NAME = Filter("REF_PIN_NAME")

DIRECTION = Filter("DIRECTION")
DIRECTION.OUT = Filter("OUT")
DIRECTION.IN = Filter("IN")
IS_CLEAR = Filter("IS_CLEAR")
IS_CLOCK = Filter("IS_CLOCK")
IS_CONNECTED = Filter("IS_CONNECTED")
IS_PRESET = Filter("IS_PRESET")
IS_LEAF = Filter("IS_LEAF")
IS_INVERTED = Filter("IS_INVERTED")
IS_RESET = Filter("IS_RESET")
IS_SET = Filter("IS_SET")
IS_LOC_FIXED = Filter("IS_LOC_FIXED")
IS_BEL_FIXED = Filter("IS_BEL_FIXED")
LOC = Filter("LOC")