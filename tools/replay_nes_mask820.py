"""Replay unchanged-game NT, CHR and register observations on the actual fitted collector RTL."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from capture_nes_mask820 import ROOT


def run(capture, board, out):
    assert os.environ["SALT_LICENSE_SERVER"] == "18000@localhost"
    out.mkdir(parents=True, exist_ok=False)
    for frame in json.loads((capture/"capture.json").read_text())["sampled"]:
        stim = out / str(frame)
        subprocess.run([sys.executable, ROOT/"tools/prepare_nes_geometry230.py",
                        "--capture",capture,"--prior",capture,"--out",stim,
                        "--first",str(frame),"--last",str(frame)],check=True)
        for ext in ("hex","palette"):
            f=stim/f"frame{frame}.{ext}"
            shutil.copyfile(f,out/f.name)
    simulate(board, out, [(f, f) for f in json.loads((capture/"capture.json").read_text())["sampled"]])


def simulate(board, out, ranges, *, adapt=None):
    assert os.environ["SALT_LICENSE_SERVER"] == "18000@localhost"
    bench=(ROOT/"tests/nes-functional/geometry230_tb.sv").read_text()
    bench=bench.replace(".frame_owned(owned)",".start_permitted(1'b1),.discard_permitted(1'b1),.frame_owned(owned)")
    bench=bench.replace('enable=1;', '''cf=$fopen($sformatf("frame%0d.query",f),"w");enable=1;''')
    bench=bench.replace('if(!reset&&enable&&tx_valid', '''if(enable && response && hit)
   $fwrite(cf,"%0d %0d %016h\\n",query_kind,query_index,data);
  if(!reset&&enable&&tx_valid''')
    bench=bench.replace("enable=0;$fclose(fd);", "enable=0;$fclose(fd);$fclose(cf);")
    (out/"mask820_tb.sv").write_text(adapt(bench) if adapt else bench)
    names=["nes_native_frame201","nes_native_planes165","nes_patch_capture181","nes_patch_rows181",
           "nes_native_compact181","nes_native_raster181","nes_native_export203"]
    q=Path("C:/altera_standard/25.1std/questa_fse/win64")
    def call(tool,args,label):
        with (out/(label+".log")).open("wb") as f:
            subprocess.run([q/(tool+".exe"),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=240)
    call("vlib",["work"],"lib")
    call("vlog",["-sv",*[board/(n+".sv") for n in names],"mask820_tb.sv"],"compile")
    failures=[]
    for frame,last in ranges:
        call("vsim",["-c","work.geometry230_tb",f"+FIRST={frame}",f"+LAST={last}",
                     "-do","onerror {quit -code 1}; run -all; quit -f"],str(frame))
        if f"PASS GEOMETRY230 frames={last-frame+1}\n" not in (out/f"{frame}.log").read_text(errors="replace"):
            failures.append(frame)
    assert not failures,failures


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("capture","board","out"):
        p.add_argument(n,type=Path)
    a=p.parse_args()
    run(a.capture.resolve(),a.board.resolve(),a.out.resolve())
