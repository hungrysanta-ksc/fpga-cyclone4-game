"""Measure available SPI intervals, receiver deadlines and packet-work floors."""
import argparse
import csv
import json
import math
from pathlib import Path

from check_nes_output970 import counters
from check_nes_plan975 import directory, read, sha
from nes_overlap1002 import ledger
from test_nes_banks557 import MASTER


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def idle(events, start, end):
    occupied=sorted((max(start,math.floor(e["start"])),min(end,math.ceil(e["clock"])))
                    for e in events if "start" in e and e["start"]<end and e["clock"]>start)
    free=[]
    for a,b in occupied:
        if start<a:
            free.append((start,a))
        start=max(start,b)
    if start<end:
        free.append((start,end))
    return free


def wire_budget(jobs, windows, joined):
    # Earliest finish for a subset dominates any later finish for its
    # successors. Preserve each section's internal order and whole packets.
    n=len(jobs)
    states={0:(0,[])}
    for mask in range(1<<n):
        if mask not in states:
            continue
        end,trace=states[mask]
        for i,j in enumerate(jobs):
            if mask>>i&1 or any(not mask>>k&1 and jobs[k]["section"]==j["section"] for k in range(i)):
                continue
            ready=max(end,j.get("assembled",j["source"]) if joined else j["source"])
            for a,b in windows:
                at=max(a,ready)
                done=at+j["duration"]
                if done<=b:
                    dest=mask|1<<i
                    if dest not in states or done<states[dest][0]:
                        states[dest]=(done,trace+[[j["index"],at,done]])
                    break
    def score(mask):
        return sum(j["wire_B"] for i,j in enumerate(jobs) if mask>>i&1)
    best=max(states,key=lambda mask:(score(mask),-states[mask][0]))
    return dict(bytes=score(best),starts=states[best][1])


def inspect(temp,phase):
    ref,_,jobs,events=ledger(temp,phase)
    last=next(j for j in jobs if j.get("token")==38)
    cutoff=read(Path(__file__).resolve().parents[1]/"analysis/stage1001-results.json")["phases"][str(phase)]["end246_vb46"]
    vstart=cutoff-22*1364
    base=counters(ref,912)
    ordinary=[j for j in jobs if j["op"] not in (1,3,7) and (j["section"] in (3,4) or j["offset"]>=1121)]
    early=min(j["source"] for j in ordinary)
    gaps=idle(events,early,last["physical_return"])
    result=dict(jobs=jobs,vblank46_start=vstart,line246_end=cutoff,baseline=base,
                idle_wire=dict(start=early,end=last["physical_return"],idle_clocks=sum(b-a for a,b in gaps),
                               longest=max(b-a for a,b in gaps),src=wire_budget(ordinary,gaps,False),
                               joined=wire_budget(ordinary,gaps,True)),runs={},guards={})
    starts={j["issue"] for j in ordinary}
    keep=[e for e in events if e.get("opcode")!="0xe1" or round(e["start"]) not in starts]
    for name,until in (("before_VBlank",vstart),("before_OBJ_return",last["physical_return"])):
        windows=idle(keep,early,until)
        result["idle_wire"][name]=dict(source=wire_budget(ordinary,windows,False),
                                        assembled=wire_budget(ordinary,windows,True))
    prefix=[r for r in rows(ref/"window.csv") if int(r["g"])<912]
    assert sum(int(r["value"]) for r in prefix if r["g"]=="909" and r["event"]=="ppu_dma" and r["op"]=="-1")==624
    result["protected"]=dict(reveal908=counters(ref,908)["reveal"],DMA909_B=624,
                             D2_910=max(e["clock"] for e in events if e.get("input_generation")==910 and e.get("opcode")=="0xd2"),
                             events_SHA256=sha(ref/"events.json"))
    for mode in ("reference-audit","joined","source","arb","tail","free","arb-stage","tail-stage"):
        kind,_,suffix=mode.partition("-")
        d=temp/(f"nes-overlap1002-{kind}-p{phase}" + ("-"+suffix if suffix else ""))
        win=rows(d/"window.csv")
        assert [r for r in win if int(r["g"])<912 and r["event"]!="group1002"]==prefix
        assert all(sha(d/f"frame-{g}.rgb")==sha(ref/f"frame-{g}.rgb") for g in range(905,913))
        c=counters(d,912)
        if mode=="reference-audit":
            assert c==base
        group=next(int(r["clock"]) for r in win if (r["g"],r["op"],r["event"])==("912","3","group1002"))
        ret=dict(tuple(map(int,line.split())) for line in (d/"returns970.txt").read_text().splitlines())[38]
        starts=[list(map(int,x.split())) for x in (d/"starts.txt").read_text().splitlines()]
        if mode=="reference-audit":
            pairs=[(j,j["issue"],j["arrive"]) for j in ordinary]
        else:
            assert len(starts)==20 and all(row[3]<2 for row in starts)
            pairs=[(j,a,b) for i,a,b,_,_,_ in starts for j in ordinary if j["index"]==i]
        # Clip actual E1 intervals at the physical final OBJ return. Never
        # count two SPI operations in the same interval or count queue ACKs.
        clocks=sum(max(0,min(ret,b)-a) for j,a,b in pairs)
        c.update(group_ready=group,group_late_ms=round((group-vstart)*1000/MASTER,4),OBJ_return=ret,
                 pre_return_wire_ms=round(1000*clocks/MASTER,4),
                 pre_return_complete_B=sum(j["wire_B"] for j,a,b in pairs if b<=ret),
                 ACK_delta_ms=round((c["ack"][0]-base["ack"][0])*1000/MASTER,4), starts=starts)
        result["runs"][mode]=c
    for mode,fault,status in ((m,f,s) for m in ("arb","tail-stage") for f,s in (("bad_seal",224),("stop_decode",228))):
        kind,_,suffix=mode.partition("-")
        d=temp/(f"nes-overlap1002-{kind}-p{phase}-{fault}" + ("-"+suffix if suffix else ""))
        guard=read(d/"result.json")
        assert guard["passed"] and (guard["commits"],guard["last_status"])==(7,status)
        assert sha(d/"retained.rgb")==sha(ref/"frame-911.rgb")
        result["guards"][mode+"-"+fault]=dict(status=status,retained=911)
    result["service"]=service(temp,phase,jobs,vstart)
    return result


def service(temp,phase,jobs,vstart):
    evidence={}
    for mode in ("reference","arb"):
        d=temp/f"nes-overlap1002-{mode}-p{phase}-audit"
        data=rows(d/"cycles1002.csv")
        assert counters(d,912)==counters(directory(temp,phase,"978returned","cold") if mode=="reference" else temp/f"nes-overlap1002-arb-p{phase}",912)
        assert len(data)==21
        lookup={}
        for r in data:
            key=tuple(int(r[k]) for k in ("op","sec","offset","token"))
            floor=6*int(r["cycles"])+2*int(r["minfetch"])-64
            assert 0<floor<=int(r["clockspan"])
            lookup[key]=dict(floor=floor,signature=int(r["signature"]))
        assert len(lookup)==21
        evidence[mode]=lookup
    # Optimistically admit every tile immediately at the first accepted E9,
    # allow independent sections, zero SPI/credits, zero gaps and no BG wait.
    # A packet service path is measured; do not extrapolate to other ABIs.
    d,_,_,_=ledger(temp,phase)
    first=min(v["seal"] for v in read(d/"e9931.json") if v["g"]==912)
    work=[]
    for j in jobs:
        k=(j["op"],j["section"],j["offset"],j.get("token",0))
        a,b=[v[k] for v in evidence.values()]
        release=math.floor(first) if j["op"]==7 else j["source"]
        work.append(dict(index=j["index"],release=release,floor=min(a["floor"],b["floor"]),same_path=a["signature"]==b["signature"]))
    def bound(at):
        return at+sum(j["floor"] for j in work if j["release"]>=at)
    at=max((j["release"] for j in work),key=bound)
    independent=dict(cut=at,finish=bound(at),minus_vblank_start=bound(at)-vstart)
    # Both implementations preserve each ordinary section's order. Propagate
    # the first packet readiness through that section, allowing all tiles to
    # be ready instantly at the first E9. This still excludes group setup.
    section_ready={}
    for j,w in zip(jobs,work,strict=True):
        w["independent_release"]=w["release"]
        if j["op"] not in (1,3,7):
            sec=j["section"]
            w["release"]=max(w["release"],section_ready.get(sec,0))
            section_ready[sec]=w["release"]
    at=max((j["release"] for j in work),key=bound)
    return dict(work=work,independent=independent,ordered=dict(cut=at,finish=bound(at),
                minus_vblank_start=bound(at)-vstart))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path);parser.add_argument("output",type=Path)
    a=parser.parse_args()
    data={p:inspect(a.temp,p) for p in (1,2)}
    a.output.write_text(json.dumps(data,indent=2)+"\n",encoding="utf8",newline="\n")
