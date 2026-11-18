"""Replay the physical collector and lease across the render-off interval with a running PPU."""
import argparse
import json
import math
import re
import shutil
from pathlib import Path

from nes_raw506 import once
from replay_nes_mask820 import simulate


def bench(template):
    s = template[:template.index(" initial begin")]
    s = once(s,"wire release_frame=manual_release|exporter_release;", """
 wire effective_release,export_permitted,retire_permitted,lease_valid,lease_fault;
 wire [15:0] captured_generation;reg retire_commit=0;""")
    s = once(s,"nes_native_frame201 frame(.*);","""nes_native_capture201 frame(
 .release_frame(exporter_release),.effective_release(effective_release),
 .source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.live_epoch(32'd1),
 .export_error(export_error),.reader_drained(1'b1),.retire_commit(retire_commit),.retire_generation(16'd1),
 .lease_valid(lease_valid),.retire_permitted(retire_permitted),.export_permitted(export_permitted),
 .captured_epoch(),.captured_generation(captured_generation),.waiting_display(),.lease_fault(lease_fault),.*);""")
    # Tie the finished reader high for this slice. Blank discard still
    # requires the board's actual export permission after retire_commit.
    s = once(s,".discard_permitted(1'b1)",".discard_permitted(export_permitted)")
    s = once(s,"wire [3:0] export_error,observe_state177;","wire [3:0] observe_state177;")
    s = once(s,"wire effective_release","wire [3:0] export_error;wire effective_release")
    return s+Path(__file__).with_name("lease850_body.sv").read_text()


def check(board, rtl, out, offsets):
    out.mkdir(parents=True,exist_ok=False)
    for f in (1544,1557):
        for ext in ("hex","palette"):
            name=f"frame{f}.{ext}"
            shutil.copyfile(rtl/name,out/name)
    result={}
    for t in sorted(set(offsets)):
        case=out/str(t)
        case.mkdir()
        for file in out.iterdir():
            if file.is_file():
                shutil.copyfile(file,case/file.name)
        simulate(board,case,[(t,t)],adapt=bench,extra_modules=("nes_native_capture201","nes_capture_lease201"))
        log=(case/f"{t}.log").read_text()
        # Questa's %d pads each decimal field.
        rows=[list(map(int,m)) for m in re.findall(r"CAP850\s+(\d+)\s+(\d+)",log)]
        drops=[list(map(int,m)) for m in re.findall(r"DROP850\s+(\d+)\s+(\d+)\s+(\d+)",log)]
        resumed=list(map(int,re.search(r"RESUME850\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",log).groups()))
        assert [c[1] for c in rows] == [d[1] for d in drops] == list(range(2,2+len(rows)))
        assert resumed == [len(rows),len(drops),12-len(rows),2+len(rows)]
        for f in (1544,1557):
            # Standalone geometry fixtures start a new generation namespace.
            # Compare every kind, index and payload bit across the boundary.
            def stripped(path):
                return [int(w,16)&~(0xffff<<77) for w in path.read_text().splitlines()]
            assert stripped(case/f"records{f}.txt")==stripped(rtl/f"frame{f}.wire")
            assert (case/f"query{f}.txt").read_text().splitlines()==(rtl/f"frame{f}.query").read_text().splitlines()
        result[t]=dict(captures=rows,discard=drops,resume=resumed)
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")


def offsets(temp, series):
    result={}
    for edition in (826,849):
        for phase in (1,2):
            run=temp/f"nes-tile821-transition-jointmirror-p{phase}-{series}-{edition}"
            gap=json.loads((run/"blank-interval.json").read_bytes())
            origin=gap["first_ready"]-240*341*4
            # Bracket the NES-domain grant at the modeled EA transaction.
            result[f"{edition}-p{phase}"]=[math.floor(gap["ea_start"]-origin), math.ceil(gap["retire_EA"]-origin)+8]
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("temp","rtl","out"):
        p.add_argument(arg,type=Path)
    p.add_argument("--offsets",nargs="+",type=int)
    p.add_argument("--series",default="850c0")
    a=p.parse_args()
    points=a.offsets or [t for pair in offsets(a.temp,a.series).values() for t in pair]
    check(a.temp/"nes-trial816-board822held",a.rtl,a.out,points)
