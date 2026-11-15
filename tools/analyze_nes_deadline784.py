# SPDX-License-Identifier: MIT
"""Decompose 954 from the preceding display through the last physical PPU write."""
import argparse
import json
from pathlib import Path
from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_rows783 import analyze
from analyze_nes_first780 import RANGES
from analyze_nes_prefix777 import ms
from test_nes_raw506_joint import PERIOD


def frame954(folder):
    windows=csv_groups(folder/"window.csv")
    w=windows[954]
    start=one([r for r in windows[953] if r["op"]==3],"reveal")
    origin=start["clock"]
    def mark(r):
        return dict(ms=ms(r["clock"]-origin),blank=r["frame"]-start["frame"],line=r["line"],clock=r["clock"])
    seal=[r for r in w if r["op"]==3]
    trace=read(folder/"events.json")
    events=[e for e in trace if e.get("generation")==954]
    wire=[e for e in events if e.get("opcode")=="0xe1"]
    packets=[bytes.fromhex(json.loads(row)[2]) for row in (folder/"packets.jsonl").read_text().splitlines()]
    heads=[]
    for tx,r in zip(wire,[r for r in w if r["event"]=="load"],strict=True):
        packet=packets[r["index"]-1]
        assert int.from_bytes(packet[8:10],"little")==954 and abs(tx["clock"]-r["clock"])<100000
        ack=one([e for e in w if e["index"]==r["index"]],"ack")
        assert tx["start"]<tx["clock"]<=r["clock"]+1<=ack["clock"]
        heads.append(dict(op=packet[0],section=packet[1],offset=int.from_bytes(packet[10:12],"little"),
            wire_start=ms(tx["start"]-origin),wire_end=ms(tx["clock"]-origin),accepted=mark(r),returned=mark(ack)))
    markers={e:mark(one(seal,e)) for e in ("load","seal","validate181","coverage212","upload165_entry","final212","reveal","ack")}
    starts=[e for e in w if e["event"]=="ppu_dma"]
    ends=[e for e in w if e["event"]=="ppu_last"]
    addresses={e["clock"]:e for e in csv_groups(folder/"seal528.csv")[954] if e["event"]=="dma"}
    transfers=[]
    for r,last in zip(starts,ends,strict=True):
        assert r["frame"]==last["frame"] and 225<=r["line"]<=last["line"]<=261
        bus=addresses.get(r["clock"],{})
        transfers.append(dict(start=mark(r),last=mark(last),size=r["value"],port=bus.get("port"),source=bus.get("src"),dest=bus.get("dst"),sealed=r["op"]==3))
    source=one(events,"source_begin")
    timing={key:ms(one(events,key)["clock"]-origin) for key in ("source_begin","planner_enter","bg_map_frozen","prepare_enter","output_enter531")}
    timing["capture_ready"]=ms(source["capture_ready"]-origin)
    rom=next(x for x in read(folder/"obj-phases.json")["954"]["cache611"] if x[-1]=="ROM" and x[0]==0)
    timing["first_BG_ROM_request"],timing["first_BG_ROM_grant"]=[ms(t-origin) for t in rom[2:4]]
    last_pop=[e for e in trace if e.get("input_generation")==953 and e.get("opcode")=="0xd2"][-1]["clock"]
    capture_start=source["capture_ready"]-240*341*4
    assert capture_start-PERIOD<=last_pop<capture_start
    previous=one([r for r in windows[952] if r["op"]==3],"reveal")
    return dict(arm=timing,packets=heads,seal=markers,DMA=transfers,interval=markers["reveal"]["blank"],
                waits=[mark(r) for r in seal if r["event"]=="wait169"],
                reveal953_clock=origin,interval953=start["frame"]-previous["frame"],
                capture_ready_clock=source["capture_ready"],first_BG_grant_clock=rom[3],
                previous_capture_edge_to_last_953_D2_ms=ms(last_pop-(capture_start-PERIOD)))


def report(temp,work,modes):
    evidence=dict(scope="Full M4 link and original 65816. Simulated SPI/IRQ/ROM arbitration. All relative 954 times start at actual 953 reveal.", builds={},phases={})
    for name,i in modes:
        src=work/f"arm{i}/src/obj-nes-100"
        guards=read(work/f"g{i}/guards.json")
        firmware=sha(src/"firmware.stm")
        assert guards["guards"]["firmware"]==firmware==read(work/f"g{i}/padding.json")["firmware"]
        evidence["builds"][name]=dict(flash=(src/"firmware.stm").stat().st_size,elf=sha(src/"sd2snes.elf"),firmware=firmware,guards=guards)
    for phase in (1,2):
        ph=evidence["phases"][phase]={}
        base=temp/f"nes-range778-763-p{phase}"
        ph["763"]=dict(frame954=frame954(base))
        ref=read(Path(__file__).resolve().parents[1]/"analysis/grant782.json")["phases"][str(phase)]["763"]
        prior=read(Path(__file__).resolve().parents[1]/"analysis/rows783.json")["phases"][str(phase)]["window"]
        ph["763"].update(dense_ms=ref["dense_ms"],dense_VBlanks=ref["dense_VBlanks"],ACK970_clock=ref["final970"])
        for name in ["783G"]+[n for n,_ in modes]:
            d=temp/(f"nes-grant783-window-p{phase}" if name=="783G" else f"nes-deadline784-{name}-p{phase}")
            r=analyze(d,base)
            if name=="783G":
                assert r["final970"]==prior["final970"] and r["first"]==prior["first"]
            else:
                assert r["firmware"]==evidence["builds"][name]["firmware"]
            starts=[x[-1] for x in r["transfers"] if x[0]=="map" and x[4]==-1 and
                any(k=="map" and max(off,x[1])<min(off+n,x[1]+x[2]) for k,off,n in RANGES)]
            dense=round(r["dense_ms"]-ref["dense_ms"],6)
            final=ms(r["final970"]-ref["final970"])
            f=frame954(d)
            ph[name]=dict(frame954=f,first969=r["first"],map_start969=starts,display=r["intervals"],dense_ms=r["dense_ms"],
                dense_VBlanks=r["dense_VBlanks"],dense_delta_ms=dense,ACK970_clock=r["final970"],ACK970_delta_ms=final,
                same_payloads_and_images=r["verified"],passed=bool(name!="783G" and evidence["builds"][name]["flash"]<=212992 and
                r["verified"]==66 and f["interval"]<=3 and all(r["intervals"][g]<=prior["intervals"][str(g)] for g in (909,960,969)) and
                r["first"]==[n for _,_,n in RANGES] and starts and max(starts)<=252 and dense<0 and final<0))
        if "raw" in ph:
            run=temp/f"nes-deadline784-raw-p{phase}"
            stop=read(temp/f"nes-deadline784-stop-raw-p{phase}"/"proof.json")
            assert stop["map_offset"]==2496 and stop["after_return"] and stop["commits"]==64
            assert stop["last_packet_status"]==0 and stop["blanks_after_STOP"]>=3
            assert stop["retained"]==sha(run/"frame-968.rgb") and stop["client"]==sha(run/"client.sfc")
            ph["raw"]["STOP_after_2496"]=stop
    return evidence


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("temp","work","out"):p.add_argument(key,type=Path)
    p.add_argument("--candidate",nargs=2,action="append",required=True)
    args=p.parse_args()
    data=report(args.temp,args.work,[(n,int(i)) for n,i in args.candidate])
    args.out.write_text(json.dumps(data,indent=2)+"\n",newline="\n")
