"""Compare independent packet-order trials by generation and by previous reveal."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from compare_nes_latency898 import CLIPS
from nes_tail1013 import ROOT, VARIANTS, WORK
from read_nes_frame900 import PERIOD
from read_nes_tail1012 import ARM_TICK, decode
from test_nes_raw506_joint import MASTER


def run_dir(temp,phase,mode):
    return temp/f"nes-tile821-late-jointmirror-p{phase}-1013c-{mode}"


def collect(d):
    outcome=json.loads((d/"joint.json").read_bytes())
    bus=json.loads((d/"events.json").read_bytes())
    assert outcome["passed"] and outcome["commits"]==8 and outcome["last_status"]==1
    with (d/"window.csv").open() as f:
        events=list(csv.DictReader(f))
    wire=[(bytes.fromhex(h),bytes.fromhex(b)) for _,_,h,b in map(json.loads,(d/"packets.jsonl").read_text().splitlines())]
    loads=json.loads((d/"loads898.json").read_bytes())
    result={}
    for i,g in enumerate(range(905,913)):
        ev=[r for r in events if int(r["g"])==g]
        heads=[(h,b) for h,b in wire if int.from_bytes(h[8:10],"little")==g]
        def event(name,op=None):
            r,=[r for r in ev if r["event"]==name and (op is None or int(r["op"])==op)]
            return [int(r[k]) for k in ("clock","frame","line")]
        seal=event("load",3)
        dma=[[int(r[k]) for k in ("value","frame","line")] for r in ev if r["event"]=="ppu_dma" and int(r["clock"])<seal[0]]
        show,ack=event("reveal"),event("ack",3)
        assert seal[0]<show[0]<ack[0]
        # Ignore transport sequence only. Include all payload bytes, bulk data,
        # identity, expanded sizes, destinations and repeated packet multiplicity.
        digest=hashlib.sha256()
        pieces=sorted(hashlib.sha256(h[:2]+h[4:]+b).digest() for h,b in heads)
        for s in pieces:
            digest.update(s)
        capture,=[e for e in bus if e.get("generation")==g and e["event"]=="source_begin"]
        pops=[e for e in bus if e.get("input_generation")==g and e.get("opcode")=="0xd2"]
        result[g]=dict(source=CLIPS["late"][i],work=loads[i],seal=seal,show=show,ack=ack,
                       input_last_D2=round(pops[-1]["clock"]),capture_ready=round(capture["capture_ready"]),
                       dma_preseal=dma,packet_digest=digest.hexdigest(),
                       rgb=hashlib.sha256((d/f"frame-{g}.rgb").read_bytes()).hexdigest(),
                       map=hashlib.sha256((d/f"map-{g}.bin").read_bytes()).hexdigest(),
                       order=[[h[0],h[1],int.from_bytes(h[10:12],"little"),len(h)-16] for h,b in heads])
    return result,outcome


def guards(mode, *, root=None):
    root=root or WORK/mode
    g=json.loads((root/"guards.json").read_bytes())
    receipt=g["cases"]["normal"]
    recovery=json.loads((root/"recovery/result.json").read_bytes())
    assert receipt["checked_retire"] and g["menu"]["rows"]["normal"]["released"] and recovery["safe_return"]
    assert g["menu"]["firmware"]==recovery["firmware_sha256"]
    fw=(root/"link/src/obj-nes-100/firmware.stm").read_bytes()
    assert hashlib.sha256(fw).hexdigest()==g["menu"]["firmware"] and len(fw)<=212992
    faults=json.loads((root/"faults.json").read_bytes())
    assert all(proof["previous_screen_retained"] and proof["commits"]==3 for proof in faults.values())
    return dict(firmware=g["menu"]["firmware"],flash=len(fw),free=212992-len(fw),
                checked_retire=True,base_menu=True,arm_cases=list(g["cases"]),client_faults=faults)


def physical(files):
    rows=[]
    for f in files:
        report=decode(f.read_bytes())
        for s in report["samples"]:
            g=s["generation"]
            r,=[r for r in report["rows"] if r["generation"]==g]
            packets=s["packets"]
            maps=[p for p in packets if p["section"]==2]
            tail=packets[maps[-1]["seq"]+1:]
            assert [(p["op"],p["payload"]) for p in tail]==[(2,201),(2,240),(9,116),(3,168)]
            last=maps[-1]["sent"]*ARM_TICK
            # Fixed observed map prefix. Even with no setup/credit/consumer cost,
            # all four SPI transactions must finish before the SEAL can be read.
            wire_ms=sum(19+p["payload"] for p in tail)*8/2625
            earliest=last-ARM_TICK+wire_ms
            latest_show=(s["e0"]+1)*ARM_TICK-r["final_ACK_to_ARM_E0_ms"][0]
            # Previous line 246 inclusive. Allow one short-line correction.
            latest_cutoff=latest_show-PERIOD+22*1364/(MASTER/1000)+4/(MASTER/1000)
            rows.append(dict(file_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),g=g,
                             map704_B=sum(p["payload"] for p in maps[-4:]),wire_floor_ms=wire_ms,
                             oam_only_min_late_line246_ms=round(earliest-latest_cutoff,4)))
    return rows


def analyze(temp,files):
    report=dict(master_Hz=MASTER,event_units=["master_clock","Mesen_frame","scanline"],
                guards={m:guards(m) for m in VARIANTS},physical=physical(files),phases={})
    ref=json.loads((ROOT/"analysis/trial1012-package.json").read_bytes())
    for phase in (1,2):
        comparison={}
        runs={}
        wire_bytes={}
        for mode in ("control",*VARIANTS):
            rows,meta=collect(run_dir(temp,phase,mode))
            assert meta["client_SHA256"]==ref["client"]
            assert meta["firmware_SHA256"]==(ref["firmware"] if mode=="control" else report["guards"][mode]["firmware"])
            runs[mode]=rows
            wire_bytes[mode]=meta["wire_B"]["0xe1"]
        assert len(set(wire_bytes.values()))==1
        for g,base in runs["control"].items():
            entry={"source":base["source"],"work":base["work"],"runs":{}}
            for mode,rows in runs.items():
                row=rows[g]
                assert all(row[k]==base[k] for k in ("work","rgb","map","packet_digest"))
                prev=rows.get(g-1)
                entry["runs"][mode]={k:row[k] for k in ("seal","show","ack","dma_preseal","capture_ready","input_last_D2")}
                if g==908:
                    entry["runs"][mode]["order"]=row["order"]
                entry["runs"][mode]["interval"]=row["show"][1]-prev["show"][1] if prev else None
                entry["runs"][mode]["delta_ms"]={k:round((row[k][0]-base[k][0])*1000/MASTER,4) for k in ("seal","show","ack")}
                if prev:
                    entry["runs"][mode]["from_prev_delta_ms"]={k:round((row[k][0]-prev["show"][0]-base[k][0]+runs["control"][g-1]["show"][0])*1000/MASTER,4) for k in ("seal","show","ack")}
            comparison[g]=entry
        # Pin actual changes on a shared 23-row frame, including coverage and size.
        fixed=comparison[908]["runs"]
        for mode in ("control",*VARIANTS):
            order=fixed[mode]["order"]
            oam=order.index([9,4,0,116])
            raw=order.index([2,5,1121,201])
            tables=order.index([2,5,1322,240])
            assert ((oam<raw<tables) if mode=="oam" else (raw<tables<oam))
            map_indices=[order.index([2,2,off,n]) for off,n in [(768,192),(960,192),(1152,192),(1344,128)]]
            first_tile=next(i for i,p in enumerate(order) if p[0]==7)
            assert (max(map_indices)<first_tile)==(mode=="map")
        report["phases"][phase]=comparison
        report.setdefault("E1_bytes",{})[phase]=wire_bytes
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("logs",type=Path,nargs=2)
    a=p.parse_args()
    result=analyze(a.temp,a.logs)
    (ROOT/"analysis/tail1013-results.json").write_text(json.dumps(result,ensure_ascii=False,indent=1)+"\n",encoding="utf8")
