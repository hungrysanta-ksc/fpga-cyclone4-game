"""Measure the SPI/DMA intersection and the actual publication deadline, in master clocks."""
import argparse
import csv
import json

from check_nes_output970 import packet_path
from check_nes_tail1013 import collect, guards
from nes_split1020 import ROOT, WORK, sha
from pathlib import Path


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def frame908(path, frames, start=None):
    g=908
    frame=frames[g]
    headers=frame["order"]
    _,ledger=packet_path(path,g,expected_shape=(len(headers),sum(h[0]==7 for h in headers)))
    def packet(op,section,offset,length):
        p,=[v for h,v in zip(headers,ledger,strict=True) if h==[op,section,offset,length]]
        return p
    first=packet(2,5,1121,201)
    tail=packet(2,5,1322,240)
    map_head=packet(2,2,768,192)
    ev=[r for r in rows(path/"window.csv") if int(r["g"])==g]
    def stamp(r):
        return [int(r[k]) for k in ("clock","frame","line")]
    beams=[r for r in rows(path/"budget685.csv") if int(r["generation"])==g]
    if start is None:
        beam=beams[0]
        start=int(beam["latch_clock"])-int(beam["h"])-(int(beam["line"])-225)*1364
    stop=start+22*1364
    early=[]
    for i,r in enumerate(ev):
        if r["event"]!="idle524":
            continue
        dma=next(x for x in ev[i+1:] if x["event"]=="ppu_dma")
        end=next(x for x in ev[i+1:] if x["event"]=="ppu_last")
        assert int(r["clock"])<int(dma["clock"])<int(end["clock"])<frame["seal"][0]
        early.append(dict(source=int(r["value"]),length=int(dma["value"]),start=stamp(dma),end=stamp(end)))
    maps=[r for r in early if r["source"]==65536+768 and r["length"]==192]
    overlap=sum(max(0,min(tail["arrive"],d["end"][0])-max(tail["issue"],d["start"][0])) for d in maps)
    included = [d for d in early if d["source"] <= 65536+768
                and d["source"]+d["length"] >= 65536+960 and d["source"]>=65536]
    enclosing_overlap = sum(max(0,min(tail["arrive"],d["end"][0])-max(tail["issue"],d["start"][0]))
                            for d in included)
    remaining=[dict(header=h,wire_clocks=p["arrive"]-max(start,p["issue"])) for h,p in zip(headers,ledger)
               if p["arrive"]>start]
    validate,=[stamp(r) for r in ev if r["event"]=="upload165_entry" and r["op"]=="3"]
    last=stamp([r for r in ev if r["event"]=="ppu_last"][-1])
    return dict(source=frame["source"],work=frame["work"],vblank225=start,line247=stop,prefix=first,
                prefix_lead=start-first["arrive"],map_head=map_head,table=tail,preseal_dma=early,
                table_map_overlap=overlap,covering_map=included,enclosing_dma_overlap=enclosing_overlap,wire_remaining_at_blank=remaining,seal=frame["seal"],
                after_validation=validate,last_ppu_byte=last,reveal=frame["show"],ack=frame["ack"],
                reveal_interval=frame["show"][1]-frames[g-1]["show"][1],end_ack=frames[912]["ack"])


def compare(temp,modes):
    result={}
    for phase in (1,2):
        prefix=f"nes-tile821-late-jointmirror-p{phase}-"
        control=temp/(prefix+"1018wire-control")
        reference,model=collect(control)
        base=frame908(control,reference)
        result[phase]={"control":base}
        for mode in modes:
            trace=temp/(prefix+"1020-"+mode)
            frames,out=collect(trace)
            for g,row in frames.items():
                for k in ("work","packet_digest","rgb","map"):
                    assert row[k]==reference[g][k],(mode,phase,g,k)
            fw=WORK/mode/"link/src/obj-nes-100/firmware.stm"
            assert out["firmware_SHA256"]==sha(fw) and out["client_SHA256"]==model["client_SHA256"]
            assert out["ROM_read_allocations"]==model["ROM_read_allocations"]
            r=frame908(trace,frames,base["vblank225"])
            r.update(firmware=sha(fw),bytes=fw.stat().st_size,allocated_reads=out["ROM_read_allocations"],
                     matched_generations=list(frames),advance_clocks={k:base[k][0]-r[k][0] for k in
                     ("seal","after_validation","last_ppu_byte","reveal","ack","end_ack")})
            result[phase][mode]=r
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("modes",nargs="+")
    p.add_argument("--guard-mode", action="append", default=[])
    a=p.parse_args()
    report=dict(reference="MMC1012",phases=compare(a.temp,a.modes))
    report["guards"]={mode:guards(mode,root=WORK/mode) for mode in a.guard_mode}
    report["dma_start_triggered_replay"]={}
    for phase in (1,2):
        data=json.loads((WORK/f"stream-grant-{phase}.json").read_bytes())
        assert data["overlap"]>0 and data["prefix"]["arrive"]<data["clock225"]
        assert data["timing"]["load"][0]<data["timing"]["upload165_entry"][0]<data["last_ppu_byte"][0]
        base=a.temp/f"nes-tile821-late-jointmirror-p{phase}-1018wire-control"
        exact=a.temp/"nes-split1020-stream-grants"/f"p{phase}"
        result=json.loads((exact/"result.json").read_bytes())
        assert result["passed"] and result["commits"]==4 and result["last_status"]==1
        for g in range(905,909):
            for name in (f"frame-{g}.rgb",f"map-{g}.bin"):
                assert sha(exact/name)==sha(base/name),(phase,name)
        data["matched_RGB_and_map"]=list(range(905,909))
        report["dma_start_triggered_replay"][phase]=data
    (ROOT/"analysis/split1020-results.json").write_text(json.dumps(report,indent=2)+"\n",newline="\n")
