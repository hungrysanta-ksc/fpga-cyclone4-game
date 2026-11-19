"""Replay the actual capture strobes, then query every byte in the emitted OBJ plans."""
from pathlib import Path
from collections import defaultdict
import json
import os
import shutil
import subprocess
import sys
from prepare_nes_tile821 import frame_fetches,samples,lanes,ADVENTURE_SHA,sha

def test(temp,root,data,rom,held=False,*,inputs=None,out=None):
    assert sha(rom)==ADVENTURE_SHA and os.environ["SALT_LICENSE_SERVER"]=="18000@localhost"
    body=rom.read_bytes()[-131072:]
    out=out or temp/("nes-output822-rtl-held" if held else "nes-output822-rtl")
    out.mkdir()
    allgroups=[]
    with (out/"stim.tsv").open("w") as stream:
        def record(*v):print(*v,file=stream)
        standard=[(data/folder,temp/f"nes-tile821-{capture}",temp/f"nes-tile821-rtl{rtl}")
                  for folder,capture,rtl in (("extra01","extra","-extra"),("demo-extra01","demo-extra","-demo-extra"),("data02","game",""))]
        for folder,capture,rtl in inputs or standard:
            fetch=frame_fetches(capture)
            for d in sorted(folder.iterdir()):
                group=len(allgroups);allgroups.append(d.name)
                caches=json.loads((d/"cache.json").read_text())
                for w in json.loads((d/"work.json").read_text()):
                    gen,f=w["g"],w["source_frame"]
                    stim=rtl/f"frame{f}.hex"
                    writes,_=samples(fetch(f),stim,body)
                    ticks=[i for i,h in enumerate(stim.read_bytes().splitlines()) if (value:=int(h,16))>>54&3==3 and (value>>49&15)>2]
                    record(0,gen,group,0)
                    for tick,(_,addr,v) in zip(ticks,(s for s in writes if s[0]),strict=True):record(1,tick,addr,v)
                    record(2,0,0,0)
                    for _,h in json.loads((d/f"frame{gen}/plans.json").read_text()):
                        q=bytes.fromhex(h)
                        if q[6]!=1:continue
                        for _,a in lanes(q):
                            tag=a//16;row=caches[str(gen)].get(str(tag%128))
                            hit=bool(row and row[0]==tag and str(a%16) in row[1])
                            record(3,a,body[a],int(hit))
                    record(4,0,0,0)
    q=Path("C:/altera_standard/25.1std/questa_fse/win64")
    board=temp/("nes-trial816-board822held" if held else "nes-trial816-board822m")
    bench=Path(__file__).resolve().with_name("mirror822_tb.sv")
    if held:
        (out/bench.name).write_text(bench.read_text().replace("nes_chr_cache611 dut","nes_chr_cache611 #(.HELD_PLAN(1)) dut"))
        bench=out/bench.name
    for tool,args in (("vlib",["work"]),("vlog",["-sv",board/"nes_chr_cache611.sv",board/"nes_obj_capture611.sv",
          bench]),("vsim",["-c","work.mirror822_tb","-do","onerror {quit -code 1}; run -all; quit -f"])):
        with (out/f"{tool}.log").open("wb") as log:
            subprocess.run([q/(tool+".exe"),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert "PASS MIRROR822" in (out/"vsim.log").read_text(errors="replace")
    write_hits(out,allgroups)
    if inputs is not None:
        return
    if held:
        assert (out/"hits.tsv").read_bytes()==(temp/"nes-output822-rtl/hits.tsv").read_bytes()
    else:shutil.copyfile(out/"hits.json",root/"hits.json")


def write_hits(out,allgroups):
    # A real clip with no OBJ plan has no lookup rows, but still has a result.
    groups={group:defaultdict(dict) for group in allgroups}
    for line in (out/"hits.tsv").read_text().splitlines():
        i,g,a,kind=map(int,line.split())
        lookup=groups[allgroups[i]][g]
        assert lookup.setdefault(a,kind)==kind
    (out/"hits.json").write_text(json.dumps(groups))

if __name__=="__main__":test(*(Path(x).resolve() for x in sys.argv[1:5]),held="--held" in sys.argv)
