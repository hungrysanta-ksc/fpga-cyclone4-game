"""Run under the existing Questa FLOAT wrapper. Compare old/new 168 MHz headers."""
import argparse
import shutil
import subprocess
from pathlib import Path
from prepare_nes_trial763 import ROOT, digest
from package_nes_trial704 import save

def run(board, base, out, bin_dir):
    out.mkdir(parents=True,exist_ok=False)
    for name in ("nes_rom_spi.sv","nes_screen_status151.sv"):
        shutil.copy(board/name,out/name)
    (out/"original.sv").write_text((base/"nes_rom_spi.sv").read_text().replace("module nes_rom_spi_check(","module original_spi_check("))
    shutil.copy(ROOT/"tools/tb_nes_frame769.sv",out)
    for name,args in (("vlib",["work"]),("vlog",["-sv","original.sv","nes_rom_spi.sv","nes_screen_status151.sv","tb_nes_frame769.sv"]),
                      ("vsim",["-c","tb_nes_frame769","-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"])):
        with (out/(name+".log")).open("wb") as f:
            subprocess.run([bin_dir/(name+".exe"),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=120,check=True)
    assert "PASS769 snapshot STOP and 400 loader frames" in (out/"vsim.log").read_text()
    save(out/"result.json",dict(passed=True,loader=digest(board/"nes_rom_spi.sv"),screen=digest(board/"nes_screen_status151.sv"),
                                reference=digest(base/"nes_rom_spi.sv"),bench=digest(out/"tb_nes_frame769.sv"),log=digest(out/"vsim.log")))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ("board","base","out","bin_dir"):p.add_argument(key,type=Path)
    a=p.parse_args();run(a.board,a.base,a.out,a.bin_dir)
