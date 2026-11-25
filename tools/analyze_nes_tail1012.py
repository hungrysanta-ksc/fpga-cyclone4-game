"""Calibrate the late packet trace against both physical runs and the two 978 schedules."""
import argparse
import hashlib
import json
from pathlib import Path
from check_nes_output970 import packet_path
from nes_display1010 import ROOT
from read_nes_display1010 import decode


def analyze(directory,temp):
    hw=json.loads((ROOT/"analysis/display1010-hardware.json").read_bytes())
    controls=json.loads((ROOT/"analysis/demo-loss1009-results.json").read_bytes())
    result={"runs":[],"replay_911":{}}
    for i,run in enumerate(hw["runs"],1):
        path=directory/f"nes-frame-mmc1010-{i}차.bin"
        assert hashlib.sha256(path.read_bytes()).hexdigest()==run["files"]["frame"]
        rows=decode(path)["rows"]
        selected=[]
        for key,lo,hi in (("1411",5500,5547),("1443",5574,5634)):
            ref=run["targets"][key]
            def shape(r):
                return tuple(r[k] for k in ("BG","OBJ","map","tiles","chunks"))+tuple(bytes.fromhex(r["descriptor_hex"])[:6])
            hits=[r for r in rows if lo<=r["tick"]<=hi and shape(r)==shape(ref)]
            assert hits and hits[0]["generation"]==ref["generation"]
            selected.append([r["generation"] for r in hits])
        result["runs"].append(dict(trial=i,map23=sum(r["map"]==23 for r in rows),candidate_generations=selected))
    for phase in (1,2):
        t=temp/f"nes-tile821-obj-jointmirror-p{phase}-978returned-cold-pair"
        commands,ledger=packet_path(t,911)
        start=controls["replay978"][str(phase)]["911"]["last_tile"]
        records=[]
        for p,r in zip((c for c in commands if c[0]==911),ledger,strict=True):
            if r["ack"]<start:
                continue
            head=bytes.fromhex(p[3])
            records.append(dict(op=r["op"],section=r["section"],payload=int.from_bytes(head[12:14],"little"),
                **{k:round((r[k]-start)*1000/controls["replay978_master_hz"],3) for k in ("issue","arrive","load","ack")}))
        assert records[-1]["op"]==3 and records[-2]["payload"]==240
        result["replay_911"][phase]=records
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("directory","temp","output"):
        p.add_argument(arg,type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(analyze(a.directory,a.temp),indent=2)+"\n",encoding="utf8")
