"""Generate stage-level RTL inputs; compare every sealed capture to the reference model."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from cross_nes1022 import ROOT, GAMES, POLICIES, analyze, replay, rom_path
from prepare_nes_kirby1022 import verify

WORK=ROOT.parent/"probes/nes-cross1022"
SIM=WORK/"rtl"


def frames(folder):
    data=(folder/"reads.bin").read_bytes()
    pos=0
    while pos<len(data):
        _,n=struct.unpack_from("<II",data,pos)
        pos+=8
        yield list(struct.iter_unpack("<IB",data[pos:pos+5*n]))
        pos+=5*n


def emit(run):
    SIM.mkdir(parents=True,exist_ok=True)
    with (SIM/"vectors.txt").open("w",encoding="ascii") as f:
        for game in GAMES:
            for records in frames(run/game):
                demand=dict(records)
                print(len(records),len(demand),file=f)
                for group in (records,demand.items()):
                    for a,v in group:
                        print(format(a,"x"),format(v,"x"),file=f)


def check(run, rom_dir, result, repeat):
    log=(SIM/"run.log").read_text()
    scores=re.findall(r"OBJ1022 (\d+(?: \d+){9})",log)
    assert len(scores)==120 and "PASS1022 120" in log
    ports=[list(map(int,r.split())) for r in re.findall(r"PORT1022 (\d+(?: \d+){3})",log)]
    assert len(ports)==120
    idx=0
    games={}
    for game,digest in GAMES.items():
        folder=run/game
        for name in ("reads.bin","windows.txt"):
            assert (folder/name).read_bytes()==(repeat/game/name).read_bytes(), (game,name)
        start=idx
        for records in frames(folder):
            counts=[replay(records,p) for p in POLICIES]
            row=[idx]+[c[k] for c in counts for k in ("primary","mirror","miss")]
            assert row==list(map(int,scores[idx].split())),(game,idx)
            idx+=1
        games[game]=dict(rom_sha256=digest,trace_sha256=hashlib.sha256((folder/"reads.bin").read_bytes()).hexdigest(),
                         windows=analyze(rom_path(rom_dir,game),folder))
        for window,rows in [("1-30",ports[start+1:start+30]),("30-60",ports[start+30:start+60])]:
            assert all(r[0]==start+i for i,r in enumerate(ports[start:start+60]))
            metrics=games[game]["windows"][window]
            assert sum(r[3] for r in rows)==metrics["policies"]["low_mirror"].get("miss",0)
            metrics["lookup_cycles"]={"normal":sum(r[1] for r in rows),"remember":sum(r[2] for r in rows)}
    arm=verify(*(rom_path(rom_dir,g).read_bytes() for g in GAMES))
    load_log=(WORK/"load/run.log").read_text()
    assert "PASS1022 786432 writes, 786432 independent CHECKs, 1536 RUN reads, STOP" in load_log
    result.write_text(json.dumps(dict(games=games,arm=arm,independent_runs_per_title=2,rtl_checked_frames=idx,
                                      psram=dict(writes=786432,checks=786432,run_reads=1536,stop=True),
                                      board_fps_kirby=None),indent=2)+"\n",encoding="utf8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["emit","check"])
    parser.add_argument("run",type=Path)
    parser.add_argument("--rom-dir",type=Path)
    parser.add_argument("--result",type=Path)
    parser.add_argument("--repeat",type=Path)
    args=parser.parse_args()
    if args.action=="emit":
        emit(args.run)
    else:
        check(args.run,args.rom_dir,args.result,args.repeat)
