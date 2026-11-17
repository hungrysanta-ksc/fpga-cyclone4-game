"""Attribute first BG latency and count PPU writes at the physical VBlank 51."""
import csv
import json
from pathlib import Path

from analyze_nes_section841 import folder, contents, window, packets, point, TILES, opening
from nes_tile842 import OUT, arm
from nes_section841 import sha


def read(path):
    return json.loads(path.read_bytes())


def measure(phase,mode,test):
    f=folder(phase,"842"+mode+test)
    rows=window(f)
    reveals=[point(r) for r in rows if r["event"]=="reveal"]
    costs=read(Path("analysis/section841-results.json"))["phases"][str(phase)]
    start=costs["VB51_start"]
    end=start+37*1364
    limit=costs["VB52_start"]+22*1364
    selected=[r for r in rows if r["g"]==910]
    if (f/"fault.json").exists() and not (f/"joint.json").exists():
        fault=read(f/"fault.json")
        def field(key,name,size):
            entry=fault[key]
            pos=entry["layout"][name]
            return int.from_bytes(bytes.fromhex(entry["bytes"])[pos:pos+size],"little")
        return dict(reveals=reveals,accepted_heads=sum(r["event"]=="load" for r in selected),
                    error=field("transport","error",1),sent=field("transport","sent",2),
                    bulk_target=field("plan","bulk_until",2),final_ACK=False)
    ref=folder(phase,"832base")
    j=read(f/"joint.json")
    assert j["passed"] and len(reveals)==6 and j["commits"]==6 and j["last_status"]==1
    assert contents(f)==contents(ref)
    for g in range(905,911):
        assert (f/f"frame-{g}.rgb").read_bytes()==(ref/f"frame-{g}.rgb").read_bytes()
    events=read(f/"events.json")
    ev=[e for e in events if e["generation"]==910]
    spi=[e for e in ev if e["event"]=="SPI"]
    plan=read(f/"plan842.json")
    dec=next(r for r in plan if r[:2]==["decode",[2,0]])
    e9=next(e for e in spi if e["opcode"]=="0xe9" and abs(e["clock"]-dec[2])<1)
    jobs=[json.loads(l) for l in (f/"producer.jsonl").read_text().splitlines()]
    zero=next(v for v in jobs if v["generation"]==910 and v["kind"]==0)
    e8=next(e for e in spi if e["opcode"]=="0xe8" and bytes.fromhex(e["reply"])[6] and
            int.from_bytes(bytes.fromhex(e["reply"])[14:18],"little")==zero["token"])
    pk=packets(f)
    bulk=[r for r in selected if r["event"]=="load" and r["op"]==7]
    first=next(r for r in bulk if r["section"]==0)
    send=[e for e in events if e.get("opcode")=="0xe1"][first["index"]-1]
    assert send["packet_opcode"]==7
    timing=dict(planner=next(e["clock"] for e in ev if e["event"]=="planner_enter"),
                E9_start=e9["start"],E9_end=e9["clock"],decode=dec[3],descriptor=zero["producer"],
                E8_start=e8["start"],E8_end=e8["clock"],E1_start=send["start"],
                E1_end=send["clock"],head=first["clock"])
    assert list(timing.values())==sorted(timing.values())
    occupancy={}
    packet_index=iter(pk)
    for e in events:
        if e["event"]!="SPI":continue
        op=e["opcode"]
        if op=="0xe1":
            data=next(packet_index)
            op=f"E1 section {data[1]}"
        if timing["planner"]<=e["start"]<e9["start"]:
            entry=occupancy.setdefault(op,dict(count=0,clocks=0))
            entry["count"]+=1
            entry["clocks"]+=e["clock"]-e["start"]
    assert next(packet_index,None) is None
    grants=[r for r in plan if r[0]=="grant"]
    assert not any(r[1]==[2,0] for r in grants)
    pins=[]
    with (f/"tile532.csv").open() as stream:
        for row in csv.DictReader(stream):
            if row["g"]=="910" and row["event"]=="tile":
                pins.append((int(row["clock"]),int(row["src"]),int(row["n"])))
    with (f/"seal528.csv").open() as stream:
        for row in csv.DictReader(stream):
            if row["g"]=="910" and row["event"]=="dma" and row["port"]=="24":
                pins.append((int(row["clock"]),int(row["src"]),int(row["bytes"])))
    dma=list(zip([r for r in selected if r["event"]=="ppu_dma"],
                 [r for r in selected if r["event"]=="ppu_last"],strict=True))
    tiles=[]
    for h in bulk:
        b=pk[h["index"]-1]
        off=int.from_bytes(b[10:12],"little")
        section=h["section"]
        size=int.from_bytes(b[14:16],"little")
        base=49152 if section else 32768
        for (kind,target),nbytes in TILES.items():
            if kind!=section:continue
            begin,endoff=max(off,target),min(off+size,target+nbytes)
            if begin>=endoff:continue
            t,n=next((t,n) for t,src,n in pins if src<=base+begin and base+endoff<=src+n)
            a,b=next((a,b) for a,b in dma if 0<=a["clock"]-t<1500 and a["value"]==n)
            tiles.append(dict(section=kind,offset=begin,bytes=endoff-begin,head=point(h),first=point(a),last=point(b)))
    assert sum(v["bytes"] for v in tiles)==176
    raw=[]
    if (f/"rows841.csv").exists():
        for row in csv.reader((f/"rows841.csv").read_text().splitlines()):
            g,bank,i,dst,t,vb,line,done=map(int,row)
            if g==910:
                a,b=next((a,b) for a,b in dma if t<=a["clock"]<b["clock"]<=done)
                assert a["value"]==64
                raw.append(point(b))
    ack=j["frames"][-1]["ACK_masterclock"]
    gaps=[b[1]-a[1] for a,b in zip(reveals[1:],reveals[2:])]
    return dict(BG=timing,BG_head_after_end51=first["clock"]-end,pre_E9_SPI=occupancy,
                physical_grants_2580=len(grants),BG_grants=0,tiles=tiles,
                tile_accepted_by_end51=sum(v["bytes"] for v in tiles if v["head"][0]<end),
                tile_DMA_in_51=sum(v["bytes"] for v in tiles if start<=v["first"][0]<v["last"][0]<end),
                tile_DMA_by_51_line246=sum(v["bytes"] for v in tiles if start<=v["first"][0]<v["last"][0]<start+22*1364),
                DMA_in_51=[dict(bytes=a["value"],start=point(a),end=point(b)) for a,b in dma if start<=a["clock"]<end],
                raw_DMA_in_51=64*sum(start<=v[0]<end for v in raw),raw=raw,
                SEAL=point(next(r for r in selected if r["event"]=="load" and r["op"]==3)),
                final_DMA=point(dma[-1][1]),clocks_past_52_246=dma[-1][1]["clock"]-limit,
                reveals=reveals,intervals=gaps,total=sum(gaps),ACK=ack,
                ACK_delta_826=ack-read(ref/"joint.json")["frames"][-1]["ACK_masterclock"],
                RGB_and_manifest_match=True,firmware=j["firmware_SHA256"],receiver=j["client_SHA256"])


def analyze():
    cases={}
    full=("prefix1","prefix6","after6","defer1","credit1","credit6","drain6")
    for p in (1,2):
        cases[p]={m:measure(p,m,"fixed") for m in ("control","early","service",*full)}
        cases[p]["837"]=measure(p,"control","original")
        cases[p]["credit1_static"]=measure(p,"credit1","static")
        cases[p]["opening"]={m:opening(folder(p,"842"+m+"refopening",True),folder(p,"823826",True))
                             for m in ("after6","credit1")}
        matched=cases[p]["control"]
        assert (matched["tile_DMA_in_51"],matched["raw_DMA_in_51"],matched["total"])==(0,192,16)
        assert matched["reveals"][-2][1]==48
        for name in ("early","service"):
            rejected=cases[p][name]
            assert rejected["error"]==5 and rejected["sent"]-rejected["bulk_target"]>4 and not rejected["final_ACK"]
        for name in full:
            row=cases[p][name]
            row["time_target"]=(row["reveals"][-2][1]==48 and row["total"]<=15 and row["ACK_delta_826"]<0 and
                                row["raw_DMA_in_51"]==192 and row["clocks_past_52_246"]<=0)
    menu={}
    for mode in full:
        binfile=arm(mode)/"src/obj-nes-100/firmware.stm"
        test=read(OUT/f"menu-{mode}.json")
        base=read(OUT/f"base-{mode}/result.json")
        assert sha(binfile)==test["firmware"]==base["firmware_sha256"]==cases[1][mode]["firmware"]
        assert base["safe_return"] and base["base_restored"] and test["rows"]["normal"]["released"]
        menu[mode]=dict(firmware_B=binfile.stat().st_size,menu_and_base=True)
    faults={}
    for fault in ("stop","damage"):
        f=folder(1,"842after6"+fault)
        t=int((f/"stop841.txt").read_text())
        u=int((f/"cancel841.txt").read_text())
        rows=window(f)
        assert u>=t and [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910))
        assert not any(r["event"] in ("ppu_dma","ppu_last","reveal") and r["clock"]>=t for r in rows)
        faults[fault]=dict(trigger=t,cancel=u)
    return dict(phases=cases,costs=menu,faults=faults,
                scope="Linked M4 + Mesen 65816, MMC826 SPI means, modeled FPGA decoder, cache, IRQ and ROM slots. Fixed boots 837 receiver through 2576 then switches receiver WRAM. ARM always linked from reset.")


if __name__=="__main__":
    Path("analysis/tile842-results.json").write_text(json.dumps(analyze(),indent=2)+"\n")
