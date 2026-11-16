"""Materialize 816/817 from the tested 815R rows and 813/814 boot paths."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import nes_rom636 as codec
from nes_raw506 import sha
from package_nes_trial811 import LONG_CLIENT, TIMED_CLIENT
from prepare_nes_longrun694 import optimal
from prepare_nes_trial802 import PROBES, rename_edition

ROOT = Path(__file__).resolve().parents[1]
WORK = PROBES / "nes-trial816"
TIMED = PROBES / "nes-output815/client"
LONG = WORK / "client817"


def clients():
    old = PROBES / "nes-complete685/client01"
    old_long = PROBES / "nes-longrun694/client01"
    assert sha(old/"sink165.sfc")==TIMED_CLIENT and sha(old_long/"sink165.sfc")==LONG_CLIENT
    rows = json.loads((ROOT/"analysis/output815-results.json").read_bytes())
    assert sha(TIMED/"sink165.sfc")==rows["phases"]["1"]["raw815"]["client"]
    body = bytearray((old_long/"body.bin").read_bytes())
    before, after = [(p/"body.bin").read_bytes() for p in (old,TIMED)]
    assert len(before)==len(after) and len(body)>len(before)
    labels = json.loads((old_long/"labels.json").read_bytes())
    end = labels["raw_boot489"]-0x7e2000
    start = labels["raw_dma489"]-0x7e2000
    assert before[:start]==after[:start] and before[end:]==after[end:]
    assert body[start:end]==before[start:end]
    body[start:end]=after[start:end]
    for k,v in json.loads((TIMED/"labels.json").read_bytes()).items():
        if start<=v-0x7e2000<end:
            labels[k]=v
    with patch.object(codec,"pack",optimal):
        codec.build(PROBES/"nes-reuse635/client04",LONG,edit_body=lambda b,l:bytes(body),allow_extension=True)
    (LONG/"labels.json").write_text(json.dumps(labels,indent=2)+"\n")
    for n in (816,817):
        parent = n-3
        rename_edition(PROBES/f"nes-prefix813/link{parent}/src",WORK/f"patch{n}",parent,n)


def board(temp,n):
    base = temp/"nes-fortress804-board"
    out = temp/f"nes-trial816-board{n}"
    out.mkdir()
    for directory in ("rtl","sys"):
        shutil.copytree(base/directory,out/directory)
    for p in base.iterdir():
        if p.is_file() and p.suffix in (".sv",".v",".vhd",".qpf",".qsf",".sdc",".hex",".tcl"):
            shutil.copyfile(p,out/p.name)
    client = TIMED if n==816 else LONG
    shutil.copyfile(client/"sink-program.hex",out/"sink-program.hex")
    rom=(client/"sink165.sfc").read_bytes()
    assert bytes.fromhex((out/"sink-program.hex").read_text())==rom[:5056]+rom[-64:]


def fit(temp,n,quartus):
    path=temp/f"nes-trial816-board{n}"
    stages=[("quartus_"+step,["board"],step) for step in ("map","fit","asm","sta")]
    reports=("report801.tcl","report_nes_oe612.tcl","report_nes_word660.tcl",
             "report_nes_reader661.tcl","phase801.tcl")
    stages.extend(("quartus_sta",["-t",name],name) for name in reports)
    for exe,args,log in stages:
        with (path/(log+".log")).open("wb") as f:
            subprocess.run([quartus/(exe+".exe"),*args],cwd=path,stdout=f,stderr=subprocess.STDOUT,check=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("clients","board","fit"))
    p.add_argument("--temp",type=Path)
    p.add_argument("--edition",type=int,choices=(816,817))
    p.add_argument("--quartus",type=Path,default=Path("C:/altera_lite/25.1std/quartus/bin64"))
    a=p.parse_args()
    if a.action=="clients":
        clients()
    elif a.action=="board":
        board(a.temp,a.edition)
    else:
        fit(a.temp,a.edition,a.quartus)
