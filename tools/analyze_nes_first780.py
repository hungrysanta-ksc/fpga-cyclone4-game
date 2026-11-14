# SPDX-License-Identifier: MIT
"""Measure verified first-VBlank intervals and keep fixed arrivals separate from the linked run."""
import argparse
import json
from pathlib import Path

from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_prefix777 import ms
from analyze_nes_tail735 import section5
from analyze_nes_tail779 import examine

RANGES = (("map",1216,192),("tile",0,16),("map",2304,192),("tile",16448,32),("map",2496,64))


def coverage(transfers, blank):
    # A selected range may be merged or split by the original DMA selector.
    out = []
    for kind,start,n in RANGES:
        covered = set()
        for k,at,length,_,frame,_ in transfers:
            if k == kind and (blank is None or blank == frame):
                covered.update(range(max(start,at),min(start+n,at+length)))
        out.append(len(covered))
    return out


def payloads(folder):
    """Resolve checked tile bulk tokens into destination bytes before comparison."""
    packets, tiles = [], {}
    for _,_,header,payload in map(json.loads,(folder/"packets.jsonl").read_text().splitlines()):
        h=bytes.fromhex(header)
        if h[8:10] != (969).to_bytes(2,"little"):
            continue
        if h[0]==7:
            data=bytes.fromhex(payload)
            start=int.from_bytes(h[10:12],"little")
            assert len(data)==int.from_bytes(h[14:16],"little")
            for i,b in enumerate(data,start):
                assert (h[1],i) not in tiles
                tiles[h[1],i]=b
        else:
            packets.append(h[:2]+h[4:])
    return sorted(packets),tiles


def linked(folder, base):
    j=read(folder/"joint.json")
    assert j["passed"] and j["commits"]==j["map_WRAM_VRAM_verified"]==66
    assert j["parameters"]==read(base/"joint.json")["parameters"]
    assert sha(folder/"client.sfc")==sha(base/"client.sfc")
    assert section5(folder)==section5(base) and payloads(folder)==payloads(base)
    for g in range(905,971):
        for name in (f"frame-{g}.rgb",f"map-{g}.bin",f"expected-{g}.bin"):
            assert sha(folder/name)==sha(base/name)
    w=csv_groups(folder/"window.csv")
    def seal(g,mark):
        return one([v for v in w[g] if v["op"]==3],mark)
    anchor=next(v for v in reversed(csv_groups(folder/"seal528.csv")[969]) if v["event"]=="dma" and v["port"]==4)
    actual=seal(969,"reveal")["frame"]
    assert any(v["clock"]==anchor["clock"] and v["frame"]==actual for v in w[969])
    target=seal(968,"reveal")["frame"]+2
    close=anchor["clock"]+(247-anchor["line"])*1364-anchor["h"]+4*(actual%2==0 and anchor["line"]>240)-4*(target%2==0)
    for n in range(target,actual):
        close-=262*1364-4*(n%2==0)
    obj=[v for v in w[969] if v["event"]=="load" and v["op"]==7 and v["section"]==1][-1]
    ret=one([v for v in w[969] if v["index"]==obj["index"]],"ack")["clock"]
    cutoff=seal(969,"load")["clock"]
    early=[v for v in w[969] if v["event"]=="idle524" and v["clock"]<cutoff]
    dma=[v for v in w[969] if v["event"]=="ppu_dma" and v["clock"]<cutoff]
    tile={v["clock"]:v["dst"] for v in csv_groups(folder/"tile532.csv").get(969,[]) if v["event"]=="tile"}
    transfers=[]
    for s,d in zip(early,dma,strict=True):
        assert 0<d["clock"]-s["clock"]<1000
        kind,at=("map",s["value"]-65536) if s["value"]>=65536 else ("tile",tile[s["clock"]])
        transfers.append([kind,at,d["value"],None,d["frame"]-target,d["line"]])
    return dict(intervals={g:seal(g,"reveal")["frame"]-seal(g-1,"reveal")["frame"] for g in (909,960,969)},
                first=coverage(transfers,-1),before_SEAL=coverage(transfers,None),transfers=transfers,
                OBJ_load=ms(obj["clock"]-close),OBJ_return=ms(ret-close),SEAL=ms(cutoff-close),
                upload=ms(seal(969,"upload165_entry")["clock"]-close),
                dense_ms=ms((seal(957,"reveal")["clock"]-seal(951,"reveal")["clock"])/6),
                final970=seal(970,"ack")["clock"],firmware=j["firmware_SHA256"],verified=66)


def analyze(temp,probe):
    result={}
    for p in (1,2):
        base=temp/f"nes-cost768-763-p{p}-ext"
        result[p]=phase={}
        phase["baseline"]=linked(base,base)
        previous=read(Path(__file__).resolve().parents[1]/"analysis/tail779.json")["phases"][str(p)]["763_obs"]
        for field in ("OBJ_load","OBJ_return","SEAL","upload","dense_ms","final970"):
            assert phase["baseline"][field]==previous[field],field
        phase["linked"]=linked(temp/f"nes-first780-gap-p{p}",base)
        control=phase["baseline"]
        def delta(r):
            r["dense_delta_ms"]=round(r["dense_ms"]-control["dense_ms"],6)
            r["final970_delta_ms"]=ms(r["final970"]-control["final970"])
        delta(phase["linked"])
        cases = [f"m{m}t{t}" for m in range(4) for t in range(3)]
        cases += ["m3t2-ready","m2t2-ready","m3t2-free","m2t2-free","m0t0-free",
                  "m3t2-map","m3t2-tile","m3t2-map-lead16","m3t2-ready-map-lead16",
                  "m3t2-ready-map-lead16-advance64","m3t2-ready-map-lead16-advance96",
                  "m3t2-ready-map-lead16-advance128","m3t2-ready-map-lead16-advance160",
                  "m3t2-ready-map-lead16-advance176"]
        for name in cases:
            d=temp/f"nes-first780-{name}-p{p}"
            key=d.name[len("nes-first780-"):-3]
            assert read(d/"audit.json")["frames"]==66
            r=examine(base,d,base,fixed=True)
            row=phase[key]={k:r[k] for k in ("intervals","OBJ_load","OBJ_return","SEAL","upload","dense_ms","final970","transfers")}
            target_rows=csv_groups(d/"window.csv")
            def header(g,mark):
                return one([v for v in target_rows[g] if v["op"]==3],mark)
            first_frame=header(968,"reveal")["frame"]+1
            row["first_DMA_last_write_lines"]=[v["line"] for v in target_rows[969]
                                               if v["event"]=="ppu_last" and v["frame"]==first_frame]
            row["reveal_line"]=header(969,"reveal")["line"]
            row["ACK969"]=header(969,"ack")["clock"]
            row["upload_to_reveal"]=[[v["event"],v["frame"]-first_frame,v["line"]]
                for v in target_rows[969] if v["op"]==3 and v["event"] in
                ("upload165_entry","wait169","reveal")]
            row["first"]=coverage(r["transfers"],-1)
            row["before_SEAL"]=coverage(r["transfers"],None)
            if not key.endswith("-free"):
                assert row["before_SEAL"]==[n for _,_,n in RANGES]
            delta(row)
        assert all(f"m{m}t{t}" in phase for m in range(4) for t in range(3))
    guards=read(probe/"guards.json")
    fw=probe/"arm01/src/obj-nes-100/firmware.stm"
    assert sha(fw)==guards["firmware"]==result[1]["linked"]["firmware"]==result[2]["linked"]["firmware"]
    stop=read(temp/"nes-first780-stop/proof.json")
    assert stop["blanks_after_STOP"]>=3 and stop["commits"]==64
    assert stop["retained"]==sha(temp/"nes-first780-gap-p1/frame-968.rgb")
    return dict(phases=result,ranges=RANGES,flash=fw.stat().st_size,guards=guards,receiver_STOP=stop,
                scope="Physical baseline MMC763. Linked M4 and original 65816 on modeled SPI/ROM/IRQ schedule. "
                      "Fixed-arrival tests modify only frame 969; 970 producer arrival times stay fixed.",
                timing="Milliseconds relative to the end of target VBlank line 246 unless stated; negative is early. "
                       "dense_ms averages six reveal intervals 951 through 957; final970 uses master clocks.",
                transfer_fields=["kind","byte offset (map) or VRAM destination (tile)","bytes",
                                 "after original output entry (fixed tests only)","frame relative to target","start line"])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("temp","probe","out"):
        parser.add_argument(name,type=Path)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+"\n",newline="\n")
