"""Boot both private ROMs on the fitted source's NES CPU/PPU, MMC3 and local RAM with ideal external ROM reads."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from nes_functional import VHDL
from prepare_nes_opening818 import ADVENTURE_SHA, ROM_SHA
from nes_raw506 import sha

board,out,cap,adv=map(Path,sys.argv[1:5])
games=sys.argv[5:] or ["captain","adventure"]
assert all(g in ("captain","adventure") for g in games)
assert os.environ["SALT_LICENSE_SERVER"]=="18000@localhost" and sha(cap)==ROM_SHA and sha(adv)==ADVENTURE_SHA
out.mkdir(parents=True,exist_ok=False)
for name in ("rtl","sys"):
    shutil.copytree(board/name,out/name)
for p in board.iterdir():
    if p.is_file() and p.suffix in (".sv",".v",".vh",".hex"):
        shutil.copyfile(p,out/p.name)
shutil.copyfile(Path(__file__).with_name("opening818_tb.sv"),out/"opening818_tb.sv")
for name,rom in (("captain",cap),("adventure",adv)):
    data=rom.read_bytes()
    for part,raw in (("prg",data[16:0x40010]),("chr",data[0x40010:])):
        (out/f"{name}-{part}.hex").write_text(raw.hex("\n")+"\n")
exe=Path("C:/altera_standard/25.1std/questa_fse/win64")
def run(log,prog,*args):
    with (out/(log+".log")).open("wb") as f:
        subprocess.run([exe/(prog+".exe"),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600 if prog=="vsim" else 600)
run("lib","vlib","work")
run("vhdl","vcom","-2008",*VHDL)
sv=re.findall(r"set_global_assignment -name (?:SYSTEMVERILOG|VERILOG)_FILE (\S+)",(board/"board.qsf").read_text())
run("vlog","vlog","-sv","-mfcu",*[v for v in sv if v!="nes_clock_pll123.v"],"opening818_tb.sv")
for name in games:
    run(name,"vsim","-L","altera_mf_ver","-c","work.opening818_tb","+game="+name,
        "-do","onerror {quit -code 1};run -all;quit -f")
    m=re.search(r"PASS818 (.+)",(out/(name+".log")).read_text(errors="replace"))
    assert m,name
    print(m[0],flush=True)
