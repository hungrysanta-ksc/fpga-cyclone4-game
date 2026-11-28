"""Run the selected board's CPU, PPU and mapper against each supplied ROM."""
import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from prepare_nes_carts1056 import ROOT, OUT
from probe_nes_carts1056 import GAMES

BIN = Path("C:/altera_standard/25.1std/questa_fse/win64")

def run(folder):
    for mapper,game in zip((3,7,21,5),GAMES):
        raw=(folder/(game+".nes")).read_bytes()
        with tempfile.TemporaryDirectory(prefix="cart-boot-") as scratch:
            job=Path(scratch)
            board=job/"core"
            shutil.copytree(OUT/f"board-{mapper}",board)
            split=16+raw[4]*16384
            (job/"prg.bin").write_bytes(raw[16:split])
            (job/"chr.bin").write_bytes(raw[split:])
            (job/"import.sv").write_text("import regs_savestates::*;\n")
            shutil.copyfile(ROOT/"tests/nes-functional/cart_boot1056_tb.sv",job/"boot.sv")
            qsf=(board/"board.qsf").read_text()
            src=lambda kind:re.findall(r"^set_global_assignment -name "+kind+r"_FILE ((?:rtl|sys)/\S+)",qsf,re.M)
            sv=src("SYSTEMVERILOG")
            steps=[("vlib",["work"]),("vcom",["-2008",*[board/p for p in src("VHDL")]]),
                   ("vlog",["-mfcu","-sv",*(["+define+CART_RAM"] if not raw[5] else []),
                            board/sv[0],"import.sv",*[board/p for p in sv[1:]],board/"cart_nrom.sv",board/"nes_probe.sv","boot.sv"]),
                   ("vsim",["-c","-L","altera_mf_ver","-suppress","3009",f"-gMAPPER={mapper}","work.cart_boot1056_tb",
                            "-do","onerror {quit -code 1}; run -all; quit -f"])]
            for name,args in steps:
                log=OUT/f"sim-{mapper}"/f"boot-{name}.log"
                with log.open("wb") as f:
                    run=subprocess.run([BIN/(name+".exe"),*args],cwd=job,stdout=f,stderr=subprocess.STDOUT,timeout=300)
                text=log.read_text(errors="replace")
                if run.returncode or "** Error" in text or (name=="vsim" and f"PASS CPU mapper={mapper} " not in text):
                    raise RuntimeError(text[-3200:])

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder",type=Path)
    run(p.parse_args().folder)
