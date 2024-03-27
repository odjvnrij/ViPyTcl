from src.tcl_process import TclProcessPopen


p = TclProcessPopen(r"C:\Xilinx\Vivado\2019.2\bin\vivado.bat", output=True)
p.run("puts $a")