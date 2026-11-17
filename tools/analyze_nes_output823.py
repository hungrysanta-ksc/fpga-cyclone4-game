"""Link returned map heads, checked empty-queue DMA and subsequent ordinary reads."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_output822 import BASE_ARM, CLIENT, CLK_MS, sha, trace


def map_tail(folder, gen):
    with (folder/"window.csv").open() as f:
        window=[{k:v if k=="event" else int(v) for k,v in row.items()}
                for row in csv.DictReader(f) if int(row["g"])==gen]
    packets=[bytes.fromhex(json.loads(s)[2]) for s in (folder/"packets.jsonl").read_text().splitlines()]
    tail=[r for r in window if r["section"]==2 and r["event"]=="ack" and r["value"]==0
          and int.from_bytes(packets[r["index"]-1][10:12],"little")==3392]
    assert len(tail)==1
    seal=next(r["clock"] for r in window if r["op"]==3 and r["event"]=="load")
    palette=next(r["clock"] for r in window if r["section"] in (3,4) and r["event"]=="load")
    ordinary=next(r["clock"] for r in window if r["section"] in (3,4,5) and r["event"]=="load")
    first=next(r["index"] for r in window if r["clock"]==ordinary)
    events=json.loads((folder/"events.json").read_text())
    issue=[e for e in events if e.get("opcode")=="0xe1"]
    assert len(issue)==len(packets) and all(e["packet_opcode"]==p[0] for e,p in zip(issue,packets))
    ordinary_wire=issue[first-1]["start"]
    map_wire=issue[tail[0]["index"]-1]["start"]
    polls=[e for e in events if e.get("opcode")=="0xe0" and map_wire<=e["start"]<ordinary_wire]
    empty=[e for e in polls if bytes.fromhex(e["reply"])[3:5]==bytes.fromhex(e["reply"])[5:7]]
    target=set(range(2240,3520))
    covered=set()
    idle=[]
    with (folder/"budget685.csv").open() as f:
        budget=[r for r in csv.DictReader(f) if int(r["generation"])==gen]
    for idx,r in enumerate(window):
        if r["event"]!="idle524" or r["value"]<65536:
            continue
        offset=r["value"]-65536
        dma=next(q for q in window[idx+1:] if q["event"]=="ppu_dma")
        end=next(q for q in window[idx+1:] if q["event"]=="ppu_last")
        item=budget[len(idle)]
        assert dma["value"]==int(item["bytes"]) and end["clock"]>=dma["clock"]>=int(item["clock"])
        span=target.intersection(range(offset,offset+dma["value"]))
        assert span.isdisjoint(covered)
        covered.update(span)
        idle.append(dict(offset=offset,bytes=dma["value"],target_bytes=len(span),vb=dma["frame"],
                         start=dma["clock"],end=end["clock"]))
    assert len(idle)==len(budget)
    return dict(target=[2240,3520],last_map_ack=tail[0]["clock"],first_ordinary=ordinary,
                first_palette_or_oam=palette,seal=seal,idle=idle,map_issue=map_wire,
                first_ordinary_issue=ordinary_wire,credit_polls_between=len(polls),empty_credit_polls=len(empty),
                before_ordinary_issue=sum(q["target_bytes"] for q in idle if q["end"]<ordinary_wire),
                before_ordinary=sum(q["target_bytes"] for q in idle if q["end"]<ordinary),
                before_palette_or_oam=sum(q["target_bytes"] for q in idle if q["end"]<palette),
                before_seal=sum(q["target_bytes"] for q in idle if q["end"]<seal))


def analyze(temp,root,variants):
    summary={}
    for name in ["base","mirror","822b"]+variants:
        rows={}
        build=root/("link-"+name)/"src/obj-nes-100/firmware.stm"
        if name=="822b":
            build=root.parent/"nes-output822/link-b/src/obj-nes-100/firmware.stm"
        arm=BASE_ARM if name in ("base","mirror") else sha(build)
        for group in ("earlyB","demoB"):
            for phase in (1,2):
                mode,tag={"base":("base","04"),"mirror":("mirror","822b"),"822b":("jointmirror","822b")}.get(name,("jointmirror","823"+name))
                d=temp/f"nes-tile821-{group}-{mode}-p{phase}-{tag}"
                baseline=temp/f"nes-tile821-{group}-base-p{phase}-04"
                row=trace(d,arm)
                for g in range(905,911):
                    for prefix,ext in (("frame","rgb"),("colors636","bin"),("map","bin"),("expected","bin")):
                        f=f"{prefix}-{g}.{ext}"
                        assert (d/f).read_bytes()==(baseline/f).read_bytes(), (d,f)
                key=f"{group}-p{phase}"
                ref=row if name=="base" else summary["base"]["runs"][key]
                row["final_delta_ms"]=round((row["final_clock"]-ref["final_clock"])/CLK_MS,5)
                if group=="demoB":
                    row["map_tail"]={str(f):map_tail(d,g) for f,g in ((2576,909),(2580,910))}
                rows[key]=row
        summary[name]=dict(flash_bytes=None if name in ("base","mirror") else build.stat().st_size,arm=arm,runs=rows)
    return summary


def qualification(summary,temp,name):
    candidate=summary[name]
    gates={"flash":candidate["flash_bytes"]<=212992}
    for phase in (1,2):
        early=candidate["runs"][f"earlyB-p{phase}"]
        late=candidate["runs"][f"demoB-p{phase}"]
        gates[f"timing_p{phase}"]=(early["interval_vblanks"][1]==4 and early["warm_vblanks"]<20
            and early["final_delta_ms"]<0 and late["interval_vblanks"][1]==3
            and late["warm_vblanks"]<17 and late["final_delta_ms"]<0)
        gates[f"dma_p{phase}"]=all(r["before_ordinary_issue"]==1280 for r in late["map_tail"].values())
    guards=[]
    for kind in ("stop","identity","crc"):
        path=temp/f"nes-tile821-demoB-jointmirror-p1-823{name}-{kind}-fence/rejection.json"
        row=json.loads(path.read_text())
        assert row["arm"]==candidate["arm"] and row["generation"]==910 and not row["seal_submitted"]
        assert row["case"]==kind
        assert (row["runtime_error"],row["window_error"])=={
            "stop":(2,2),"identity":(5,8),"crc":(5,4)
        }[kind]
        guards.append(row)
    cpu=json.loads((temp/"nes-output823-cpustop/result.json").read_text())
    assert cpu["client"]==CLIENT and cpu["passed"] and len(cpu["cases"])==11 and len(cpu["receipts"])==6
    return dict(candidate=name,gates=gates,passed=all(gates.values()),arm_faults=guards,client_guards=cpu,
                scope="Two six-picture emulator replays, four warm intervals per clip. MMC820 measured SPI averages, ARM CPI=2, existing ROM grant calendar and verified 822 cache responses. No new physical FPS measurement.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("temp","root","out"):
        p.add_argument(name,type=Path)
    p.add_argument("variants",nargs="+")
    p.add_argument("--qualify")
    a=p.parse_args()
    summary=analyze(a.temp,a.root,a.variants)
    result=dict(comparisons=summary)
    if a.qualify:
        result["qualification"]=qualification(summary,a.temp,a.qualify)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
