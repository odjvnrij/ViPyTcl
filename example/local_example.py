from ViPyTcl import VivadoPrj

if __name__ == '__main__':
    prj = VivadoPrj()
    prj.tcl("puts {Remote hello world}")
    prj.tcl("set a 10")
    prj.tcl("set b 20")
    result = prj.tcl("expr [expr $a + $b]")[0]
    print(f"result: {result}")

    prj.open_prj(r"D:\XXX\XXX.xpr")
    prj.open_run("impl_1")
    bit_file = "./bitstream.bit"
    prj.write_bits(bit_file, force=True)
    prj.program_bits(bit_file)
    prj.exit()
