"""Cycle-by-cycle source equivalence at maximum counts, cancellation and backpressure."""
import argparse
import shutil
import subprocess
from pathlib import Path
from nes_raw506 import once


def test(a):
    a.out.mkdir(parents=True,exist_ok=False)
    for label,board in (("reference",a.base),("candidate",a.board)):
        src=(board/"nes_native_export203.sv").read_text()
        (a.out/(label+".sv")).write_text(once(src,"module nes_native_export203", "module "+label),newline="\n")
    shutil.copyfile(Path(__file__).with_name("nes_record657_tb.sv"),a.out/"bench.sv")
    for tool,args in (("vlib",["work"]),("vlog",["-sv","reference.sv","candidate.sv","bench.sv"]),
                      ("vsim",["-c","-quiet","bench","-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"])):
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
    assert "PASS657" in (a.out/"vsim.log").read_text()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("out","base","board","bin"):p.add_argument("--"+name,type=Path,required=True)
    test(p.parse_args())
