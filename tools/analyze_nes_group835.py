"""Reconcile individual DMA clocks with the display and target-bank receipts."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map830 import packets, window
from analyze_nes_seal831 import measure
from nes_group835 import OUT, PROBES
from nes_raw506 import sha


def read(folder,ref,baseline):
    r=measure(folder,ref)
    w=window(folder)
    data=list(csv.DictReader((folder/"seal528.csv").read_text().splitlines()))
    dma=[e for e in data if e["g"]=="909" and e["event"]=="dma"]
    raw=[(int(e["dst"]),int(e["bytes"])) for e in dma if e["port"]=="24" and 0x5000<=int(e["dst"])<0x5100]
    assert raw==[(0x5000,64),(0x5002,64),(0x5020,64)]
    end=r["milestones"]["SEAL_accept"][0]
    tiles=[e for e in dma if e["port"]=="24" and end<int(e["clock"])<int(next(v["clock"] for v in dma if v["dst"]=="20480" and v["bytes"]=="64"))]
    edges=[(e["event"],e["clock"]) for e in w if e["g"]==909 and e["event"]=="ppu_last"]
    trace=[]
    prev=0
    for e in tiles:
        clock=int(e["clock"])
        i=data.index(e)
        command=next(int(v["clock"]) for v in reversed(data[:i]) if v["event"]=="command")
        latch=next((int(v["clock"]) for v in reversed(data[:i]) if v["g"]=="909" and v["event"]=="latch" and prev<int(v["clock"])<=command),None)
        last=next(t for _,t in edges if t>clock)
        trace.append(dict(size=int(e["bytes"]),dma=clock,last=last,command_to_DMA=clock-command,
                          latch_to_command=None if latch is None else command-latch,
                          previous_end_to_latch=latch-prev if prev and latch else None))
        prev=last
    first_raw=next(int(e["clock"]) for e in dma if e["dst"]=="20480" and e["bytes"]=="64")
    raw_last=next(t for _,t in edges if t>max(int(e["clock"]) for e in dma if e["port"]=="24" and 0x5000<=int(e["dst"])<0x5100))
    raw_point=next(e for e in w if e["event"]=="ppu_last" and e["clock"]==raw_last)
    final_latch=next((e for e in data if e["event"]=="latch" and e["g"]=="909" and raw_last<int(e["clock"])<r["palette_complete"][0]),None)
    gate_clock=None
    if final_latch and raw_point["frame"]==48 and 247<=int(final_latch["line"])<=261:
        gate_clock=(int(final_latch["line"])-247)*1364+int(final_latch["h"])+1
    pk=packets(folder)
    spi=json.loads((folder/"events.json").read_bytes())
    e1=[e for e in spi if e.get("opcode")=="0xe1"]
    assert len(e1)==len(pk)
    indices=[i for i,b in enumerate(pk,1) if int.from_bytes(b[8:10],"little")==910 and b[1]==2]
    i,j=indices[3:5]
    ack=next(e for e in w if e["index"]==i and e["event"]=="ack")
    load=next(e for e in w if e["index"]==j and e["event"]=="load")
    polls=[e for e in spi if e.get("opcode")=="0xe0" and e1[i-1]["clock"]<=e["start"]<e1[j-1]["start"]]
    ranges=[(e[0],e[2]) for e in r["map2580"]]
    delta=r["last_ACK"]-baseline["last_ACK"]
    d2572=r["reveals"][3][0]-baseline["reveals"][3][0]
    if "fixed" in folder.name:
        assert r["reveals"][:4]==baseline["reveals"][:4] and r["ACK2572"]==baseline["ACK2572"]
    log=folder/"group835.txt"
    return dict(intervals=r["intervals"],delta_ACK=delta,last_ACK=r["last_ACK"],delta2572=d2572,
                reveal2576=r["reveals"][4],palette=r["palette_complete"],OAM=r["OAM_complete"],
                tile_trace=trace,raw_B=sum(n for _,n in raw),raw_first=first_raw,
                raw_complete=[raw_last,raw_point["frame"],raw_point["line"]],
                final_latch=[int(final_latch[k]) for k in ("clock","line","h")] if final_latch else None,
                minimum_advance_to_line246_clocks=gate_clock,map2580=ranges,
                map4_ack=[ack[k] for k in ("clock","frame","line")],map5_load=[load[k] for k in ("clock","frame","line")],
                E0_between_map_E1=len(polls),group_trace=log.read_text().splitlines() if log.exists() else None,
                gate=(d2572==0 and r["all_DMA_by_VB48"] and r["reveals"][4][1]==48 and
                      ranges==[(768,51),(704,52)] and sum(r["intervals"])<16 and delta<0))


def analyze(temp):
    report={}
    for phase in (1,2):
        prefix=f"nes-tile821-demoB-jointmirror-p{phase}-"
        ref=temp/(prefix+"832base")
        base=measure(ref,ref)
        variants=["832base","834bgdirtyinspectfixed","835onceinspectfixed","835progressinspectfixed"]
        for mode in ("group","warm"):
            variants+=["835bgdirty"+mode+"fixed","835progress"+mode+"fixed","835progress"+mode]
        variants+=["835oncewarmfixed","835oncewarm"]
        report[str(phase)]={k:read(temp/(prefix+k),ref,base) for k in variants}
    costs={}
    for mode in ("once","progress"):
        image=PROBES/f"nes-output823/link-835{mode}/src/obj-nes-100/firmware.stm"
        menu=json.loads((OUT/f"menu-{mode}.json").read_bytes())
        recovery=json.loads((OUT/f"base-{mode}/result.json").read_bytes())
        assert menu["firmware"]==recovery["firmware_sha256"]==sha(image)
        assert menu["rows"]["normal"]["released"] and recovery["safe_return"] and recovery["base_restored"]
        costs[mode]=dict(sha256=sha(image),Flash_B=image.stat().st_size,menu=True,base=True)
    for kind in ("group","warm"):
        build=json.loads((OUT/f"client-{kind}/build.json").read_bytes())
        costs[kind]=dict(ROM_B=build["physical_ROM_B"],free_B=build["physical_free_B"],
                         sha256=sha(OUT/f"client-{kind}/sink165.sfc"))
    guards={}
    for fault,value in (("stop",228),("coverage",224)):
        folder=temp/("nes-tile821-demoB-jointmirror-p1-835warmguard"+fault)
        events=window(folder)
        assert [e["g"] for e in events if e["event"]=="reveal"]==[905,906,907,908]
        assert [(e["g"],e["op"],e["value"]) for e in events if e["event"]=="ack" and e["value"]>=224]==[(909,3,value)]
        guards[fault]={"SEAL_return":value,"published_before_fault":4}
        if fault=="stop":
            clk=int((folder/"injected835.txt").read_text())
            assert not any(e["event"] in ("ppu_dma","ppu_last") and e["clock"]>=clk for e in events)
            guards[fault]["clock"]=clk
    return dict(phases=report,images=costs,guards=guards)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp),indent=2)+"\n")
