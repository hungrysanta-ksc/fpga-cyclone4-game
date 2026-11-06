"""Exercise rejected successors and STOP on the unmodified, fitted MMC643 RTL."""
import argparse
from pathlib import Path
import json
import shutil
import subprocess
from check_nes_fault641 import digest, evidence, MODULES, ROOT


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("board","bin","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    pkg=evidence("reject643-package.json")
    sof=digest(a.board/"output_files/board.sof")
    assert sof==pkg["board"]["SHA"]["board.sof"]
    a.out.mkdir(parents=True,exist_ok=False)
    files=[f"nes_{m}.sv" for m in MODULES]+["nes_native_export203.sv"]
    for f in files:
        shutil.copyfile(a.board/f,a.out/f)
    for f in ("spi200_bus.svh","reject643.svh","fault641_tb.sv"):
        shutil.copyfile(ROOT/"tests/nes-functional"/f,a.out/f)
    commands=[("vlib","lib",["work"]),("vlog","compile",["-sv","+define+WITNESS642+REJECT643+DEFER643",*files,"fault641_tb.sv"])]
    for g in (32,97):
        commands.append(("vsim",str(g),["-c","fault641_tb",f"-gGEN643={g}","-gHOST_PHASE=8","-gNES_HALF=23.281",
                        "-gSPI_HALF=190.476","-do","onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0"]))
    for tool,label,args in commands:
        log=a.out/(label+".log")
        with log.open("wb") as f:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120,check=True)
        if tool=="vsim":
            assert f"PASS643 gen={label} STOP" in log.read_text()
    (a.out/"result.json").write_text(json.dumps(dict(SOF=sof,healthy_release_and_STOP=[32,97],
                rtl={n:digest(a.out/n) for n in files},logs={n:digest(a.out/(n+".log")) for n in ("32","97")}),indent=2)+"\n")
