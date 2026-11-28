"""Compare 1061/1062 movement windows from the same slot and audit the 1062 stop records."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
from statistics import mean

from analyze_dq4_movement1061 import analyze, decode

def compare(folder):
    runs=[]
    groups=[]
    for version in (1061,1062):
        paths=sorted(folder.glob(f"nes-frame-debug{version}-*.bin"))
        paths=[p for p in paths if p.read_bytes()[12:16]==bytes.fromhex("b92bc69a")]
        if len(paths)!=2:
            raise ValueError(f"expected two DQ4 runs for {version}")
        runs.extend(paths)
        by_position=defaultdict(list)
        for path in paths:
            _,rows=decode(path.read_bytes())
            for a,b in zip(rows,rows[1:]):
                pos=tuple(b[k] for k in ("x","y","direction","dirty","tile_bytes"))
                by_position[pos].append(b["at_ms"]-a["at_ms"])
        groups.append(by_position)
    data=analyze(runs)
    data["runs"]={Path(k).name:v for k,v in data["runs"].items()}
    common=groups[0].keys() & groups[1].keys()
    data["pooled_workload"]=dict(positions=len(common),
        intervals=[sum(len(g[k]) for k in common) for g in groups],
        gap_ms=[round(mean(mean(g[k]) for k in common),3) for g in groups])
    data["sessions"]={}
    for path in sorted(folder.glob("nes-frame-debug1062-*.bin")):
        hashes={}
        for kind in ("game-last","progress","frame","stop"):
            suffix=".txt" if kind in ("progress","game-last") else ".bin"
            blob=path.with_name(path.name.replace("nes-frame","nes-"+kind)).with_suffix(suffix).read_bytes()
            hashes[kind]=sha256(blob).hexdigest()
            if kind=="game-last":
                terminal=dict(item.split("=",1) for item in blob.decode().split())
                assert all(terminal[key]==value for key,value in (("start","1"),("err","0"),("rom","0"),("stop","1"),("base","1")))
            if kind=="progress":
                events=sorted((int(i),v.decode()) for i,v in re.findall(rb'DEBUG1062 seq=(\d+) stage=(\w+)',blob))
                assert events[-1][1]=="MENU_PREPARED"
        data["sessions"][path.stem]=dict(terminal=terminal, latest_stage=events[-1], sha256=hashes)
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    p.add_argument("report",type=Path)
    a=p.parse_args()
    a.report.write_bytes((json.dumps(compare(a.folder),indent=2,ensure_ascii=False)+"\n").encode())
