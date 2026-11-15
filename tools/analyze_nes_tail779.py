# SPDX-License-Identifier: MIT
"""Partition shared wire time separately from concurrent 65816 work at the 969 deadline."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_prefix777 import ms
from analyze_nes_tail735 import section5


def examine(source, receiver, reference, *, fixed=False):
    j=read(source/"joint.json")
    assert j["passed"] and j["commits"]==j["map_WRAM_VRAM_verified"]==66
    assert j["parameters"]==read(reference/"joint.json")["parameters"]
    assert sha(source/"client.sfc")==sha(receiver/"client.sfc")==sha(reference/"client.sfc")
    assert section5(source)==section5(reference)
    for g in range(905,971):
        for n in (f"expected-{g}.bin",f"map-{g}.bin",f"frame-{g}.rgb"):
            assert sha(reference/n)==sha(source/n)==sha(receiver/n)
    w=csv_groups(receiver/"window.csv")
    q=w[969]
    def show(g,mark):
        return one([r for r in w[g] if r["op"]==3],mark)
    def delta(g):
        return show(g,"reveal")["frame"]-show(g-1,"reveal")["frame"]
    reveals=show(969,"reveal")
    anchor=next(r for r in reversed(csv_groups(receiver/"seal528.csv")[969]) if r["event"]=="dma" and r["port"]==4)
    actual=reveals["frame"]
    assert any(row["clock"]==anchor["clock"] and row["frame"]==actual and row["event"]=="ppu_dma" for row in q)
    target=show(968,"reveal")["frame"]+2
    begin=anchor["clock"]-(anchor["line"]-225)*1364-anchor["h"]+4*(actual%2==0 and anchor["line"]>240)
    for n in range(actual-1,target-1,-1):
        begin-=262*1364-4*(n%2==0)
    close=begin+22*1364-4*(target%2==0)
    def relative(v):
        return ms(v-close)
    markers=show(969,"load")["clock"],show(969,"seal")["clock"],show(969,"validate181")["clock"],show(969,"coverage212")["clock"],show(969,"upload165_entry")["clock"]
    seal,_,_,_,upload=markers
    ev=[r for r in read(source/"events.json") if r.get("generation")==969]
    output=one(ev,"output_enter531")["clock"]
    spi=[r for r in ev if r["event"]=="SPI"]
    pkts=[r for r in q if r["event"]=="load"]
    last_obj=[r for r in pkts if r["op"]==7 and r["section"]==1][-1]
    obj=last_obj["clock"]
    tx=[r for r in spi if r["opcode"]=="0xe1"]
    def commands(d):
        rows=[(bytes.fromhex(h),tile) for _,_,h,tile in map(json.loads,(d/"packets.jsonl").read_text().splitlines())]
        return [(h,tile) for h,tile in rows if h[8:10]==(969).to_bytes(2,"little")]
    cmds=commands(source)
    if fixed:
        cmds=[(bytes.fromhex(h),tile) for _,h,tile in (s.split("\t") for s in (receiver/"arrivals.tsv").read_text().splitlines()[:-1]) if bytes.fromhex(h)[8:10]==(969).to_bytes(2,"little")]
    assert sorted((h[:2]+h[4:],t) for h,t in cmds)==sorted((h[:2]+h[4:],t) for h,t in commands(reference))
    entries=[(h,r) for (h,_),r in zip(cmds,pkts,strict=True)]
    table,=[r for h,r in entries if h[1]==5 and len(h)==256 and int.from_bytes(h[10:12],"little")>1121]
    ret=one([r for r in q if r["index"]==table["index"]],"ack")["clock"]
    objret=one([r for r in q if r["index"]==last_obj["index"]],"ack")["clock"]
    selected=[r for r in q if r["event"]=="idle524" and r["clock"]<seal]
    dma=[r for r in q if r["event"]=="ppu_dma" and r["clock"]<seal]
    tiles={r["clock"]:r["dst"] for r in csv_groups(receiver/"tile532.csv").get(969,[]) if r["event"]=="tile"}
    transfers=[]
    for sel,d in zip(selected,dma,strict=True):
        assert 0<d["clock"]-sel["clock"]<1000
        kind,at=("map",sel["value"]-65536) if sel["value"]>=65536 else ("tile",tiles[sel["clock"]])
        transfers.append([kind,at,d["value"],d["clock"]>output,d["frame"]-target,d["line"]])
    known=[("map",1216,192),("tile",0,16),("map",2304,192),("tile",16448,32),("map",2496,64)]
    preserved=sum(n for kind,at,n in known if any(k==kind and a<=at and at+n<=a+b for k,a,b,*_ in transfers))
    out=dict(intervals={g:delta(g) for g in (909,960,969)},dense_ms=ms((show(957,"reveal")["clock"]-show(951,"reveal")["clock"])/6),
             final970=show(970,"ack")["clock"],final969=show(969,"ack")["clock"],transfers=transfers,pre496=preserved,
             cutoff=close,OBJ_load=relative(obj),OBJ_return=relative(objret),table_load=relative(table["clock"]),
             table_return=relative(ret),table_service_ms=ms(ret-table["clock"]),SEAL=relative(seal),upload=relative(upload),
             check_stages_ms=[ms(b-a) for a,b in zip(markers,markers[1:])],SEAL_to_upload_ms=ms(upload-seal),
             verified=66)
    if not fixed:
        rows=[]
        for (h,r),s in zip(entries,tx,strict=True):
            assert s["bytes"]==len(h)+3 and s["clock"]<=r["clock"]+1
            if r["index"] in (last_obj["index"],table["index"],pkts[-1]["index"]):
                rows.append(dict(op=h[0],section=h[1],B=s["bytes"],E1=relative(s["start"]),end=relative(s["clock"]),
                                 wire_ms=ms(s["clock"]-s["start"]),PUSH_to_load_ms=ms(r["clock"]-s["clock"])))
        # Intersect each actual bus occupation with the interval. CRC, packet
        # checks and DMA on the other processor overlap this independent ledger.
        ledger=Counter()
        for s in spi:
            ledger[s["opcode"]]+=max(0,min(seal,s["clock"])-max(obj,s["start"]))
        assert all(a["clock"]<=b["start"] for a,b in zip(spi,spi[1:]))
        occupied=sum(ledger.values())
        assert 0<=occupied<=seal-obj
        out.update(wire=rows,OBJ_load_to_SEAL_ms=ms(seal-obj),bus_ms={k:ms(t) for k,t in ledger.items() if t},
                   between_transactions_ms=ms(seal-obj-occupied))
    last_write=[r for r in q if r["event"]=="ppu_last" and r["clock"]<seal]
    assert len(last_write)==len(transfers)
    required_end=[]
    for tr,last in zip(transfers,last_write):
        kind,at,n=tr[:3]
        if any(kind==k and at<=o and o+size<=at+n for k,o,size in known):
            required_end.append(last["clock"])
    if preserved==496:
        # These DMA and the measured SEAL validation run on one CPU. With
        # the same ordering they cannot overlap, even with free SPI/credit.
        earliest=max(max(required_end),objret)+(upload-seal)
        out.update(last_required_DMA_end=relative(max(required_end)),
                   DMA_plus_check_floor=relative(max(required_end)+upload-seal),
                   zero_wire_upload_floor=relative(earliest))
    out["OBJ_load_to_return_ms"]=ms(objret-obj)
    out["table_CPU_marks_ms"]={r["event"]:ms(r["clock"]-table["clock"]) for r in q
                                if r["index"]==table["index"] and r["event"].startswith("tail779_")}
    return out


def analyze(t,probe):
    phases={}
    for p in (1,2):
        r=phases[p]={}
        for n in (763,767):
            base=t/f"nes-cost768-{n}-p{p}-ext"
            for mode in (("obs","pack","floor","hold") if n==767 else ("obs","pack")):
                folder=t/f"nes-tail779-{mode}-{n}-p{p}"
                assert read(folder/"audit.json")["frames"]==66
                r[f"{n}_{mode}"]=examine(base,folder,base,fixed=mode!="obs")
        for name in ("wait","split","physical"):
            folder=t/f"nes-tail779-{name}-p{p}"
            r[name]=examine(folder,folder,t/f"nes-cost768-763-p{p}-ext" if name=="physical" else base)
        for name,row in r.items():
            parent=r["763_obs" if name.startswith("763") or name=="physical" else "767_obs"]
            row["parent_dense_delta_ms"]=round(row["dense_ms"]-parent["dense_ms"],6)
            row["parent_final970_delta_ms"]=ms(row["final970"]-parent["final970"])
    builds={}
    for i in (1,2,3):
        arm=probe/f"arm0{i}/src/obj-nes-100"
        guards=read(probe/f"guards{i}.json")
        assert guards["firmware"]==sha(arm/"firmware.stm")
        builds[i]=dict(flash=(arm/"firmware.stm").stat().st_size,ELF=sha(arm/"sd2snes.elf"),
                       bss=int((probe/f"arm0{i}/size.log").read_text().splitlines()[-1].split()[2]),guards=guards)
    for p,phase in phases.items():
        for i,name in enumerate(("wait","split","physical"),1):
            link=read(t/f"nes-tail779-{name}-p{p}"/"joint.json")
            assert link["firmware_SHA256"]==builds[i]["guards"]["firmware"]
        assert phase["767_obs"]["pre496"]==496
        assert phase["767_hold"]["pre496"]==496
    tests={name:read(t/f"nes-tail779-{name}"/"proof.json") for name in ("stop","bad-order")}
    assert tests["stop"]["commits"]==64 and tests["stop"]["blanks_after_STOP"]>=3
    assert tests["bad-order"]["reject"]==224 and tests["bad-order"]["commits"]==64
    return dict(phases=phases,builds=builds,receiver_guards=tests)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("temp","probe","out"):
        parser.add_argument(arg,type=Path)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+"\n",newline="\n")
