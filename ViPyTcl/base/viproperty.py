from .filter import Filter


class ViProperty(Filter):
    pass


""" Common Propertys """
NAME = ViProperty("NAME")
CLASS = ViProperty("CLASS")
TYPE = ViProperty("TYPE")
""" Common Propertys """

FILE_TYPE = ViProperty("FILE_TYPE")
FILE_TYPE.Verilog = ViProperty("Verilog")
FILE_TYPE.VerilogHeader = ViProperty("VerilogHeader")
FILE_TYPE.VerilogTemplate = ViProperty("VerlogTemplate")
FILE_TYPE.SystemVerilog = ViProperty("SystemVerilog")
FILE_TYPE.VHDL = ViProperty("VHDL")
FILE_TYPE.VHDL2008 = ViProperty("VHDL2008")
FILE_TYPE.VHDLTemplate = ViProperty("VHDLTemplate")
FILE_TYPE.EDIF = ViProperty("EDIF")
FILE_TYPE.XDC = ViProperty("XDC")
FILE_TYPE.IP = ViProperty("IP")
FILE_TYPE.TCL = ViProperty("TCL")
FILE_TYPE.SystemC = ViProperty("SystemC")
FILE_TYPE.BlockDesign = ViProperty("BlockDesign")
FILE_TYPE.MemoryInitializationFiles = ViProperty("MemoryInitializationFiles")

USED_IN_IMPLEMENTATION = ViProperty("USED_IN_IMPLEMENTATION")
USED_IN_SYNTHESIS = ViProperty("USED_IN_SYNTHESIS")
USED_IN_SIMULATION = ViProperty("USED_IN_SIMULATION")

IS_ENABLED = ViProperty("IS_ENABLED")
IS_AVAILABLE = ViProperty("IS_AVAILABLE")
IS_GENERATED = ViProperty("IS_GENERATED")
IS_GLOBAL_INCLUDE = ViProperty("IS_GLOBAL_INCLUDE")
IS_NGC_WRAPPER = ViProperty("IS_NGC_WRAPPER")

DRIVER_COUNT = ViProperty("DRIVER_COUNT")
FLAT_PIN_COUNT = ViProperty("FLAT_PIN_COUNT")
IS_CONTAIN_ROUTING = ViProperty("IS_CONTAIN_ROUTING")
IS_INTERNAL = ViProperty("IS_INTERNAL")
IS_REUSED = ViProperty("IS_REUSED")
IS_ROUTE_FIXED = ViProperty("IS_ROUTE_FIXED")
MARK_DEBUG = ViProperty("MARK_DEBUG")
PARENT = ViProperty("PARENT")
PIN_COUNT = ViProperty("PIN_COUNT")

ROUTE_STATUS = ViProperty("ROUTE_STATUS")
ROUTE_STATUS.UNPLACED = ViProperty("UNPLACED")
ROUTE_STATUS.INTRASITE = ViProperty("INTRASITE")

SINK_COUNT = ViProperty("SINK_COUNT")
SINK_COUNT.SIGNAL = ViProperty("SIGNAL")

IS_BLACKBOX = ViProperty("IS_BLACKBOX")
IS_DEBUGGABLE = ViProperty("IS_DEBUGGABLE")
IS_MATCHED = ViProperty("IS_MATCHED")
IS_ORIG_CELL = ViProperty("IS_ORIG_CELL")
IS_PRIMITIVE = ViProperty("IS_PRIMITIVE")
IS_SEQUENTIAL = ViProperty("IS_SEQUENTIAL")
LINE_NUMBER = ViProperty("LINE_NUMBER")
REF_NAME = ViProperty("REF_NAME")
REF_PIN_NAME = ViProperty("REF_PIN_NAME")

DIRECTION = ViProperty("DIRECTION")
DIRECTION.OUT = ViProperty("OUT")
DIRECTION.IN = ViProperty("IN")
IS_CLEAR = ViProperty("IS_CLEAR")
IS_CLOCK = ViProperty("IS_CLOCK")
IS_CONNECTED = ViProperty("IS_CONNECTED")
IS_PRESET = ViProperty("IS_PRESET")
IS_LEAF = ViProperty("IS_LEAF")
IS_INVERTED = ViProperty("IS_INVERTED")
IS_RESET = ViProperty("IS_RESET")
IS_SET = ViProperty("IS_SET")
IS_LOC_FIXED = ViProperty("IS_LOC_FIXED")
IS_BEL_FIXED = ViProperty("IS_BEL_FIXED")
LOC = ViProperty("LOC")

TARGET_SIMULATOR = ViProperty("TARGET_SIMULATOR")
TARGET_SIMULATOR.Xsim = ViProperty("Xsim")
TARGET_SIMULATOR.ModelSim = ViProperty("ModelSim")
TARGET_SIMULATOR.VCS = ViProperty("VCS")
TARGET_SIMULATOR.Riviera = ViProperty("Riviera")
TARGET_SIMULATOR.ActiveHDL = ViProperty("ActiveHDL")