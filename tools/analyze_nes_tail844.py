"""Reconcile actual OAM stores, queue returns, SPI packets, 65816 DMA and display."""
import csv
import json
from pathlib import Path

from analyze_nes_oam840 import decode_oam
from analyze_nes_section841 import folder, opening, packets, point, window
from analyze_nes_seal831 import contents
from nes_tail844 import MODES, OUT, arm, base


def read(path):
    return json.loads(path.read_bytes())


def timing(f, ref, cutoff):
    w=window(f)
    shown=[point(r) for r in w if r["event"]=="reveal"]
    assert len(shown)==6
    for g in range(905,911):
        assert (f/f"frame-{g}.rgb").read_bytes()==(ref/f"frame-{g}.rgb").read_bytes()
    rows=[r for r in w if r["g"]==910]
    packets_seen=[r for r in rows if r["event"]=="load" and (r["section"]==4 or r["op"]==3)]
    assert len(packets_seen)==4
    heads=[]
    for h in packets_seen:
        a=next(r for r in rows if r["event"]=="ack" and r["index"]==h["index"])
        heads.append(dict(index=h["index"],op=h["op"],head=point(h),ACK=point(a)))
    dma=list(zip((r for r in rows if r["event"]=="ppu_dma"),
                 (r for r in rows if r["event"]=="ppu_last"),strict=True))
    gaps=[b[1]-a[1] for a,b in zip(shown[1:],shown[2:])]
    last_tile=next(r for r in reversed(rows) if r["op"]==7 and r["event"]=="ack")
    upload=next(r for r in rows if r["event"]=="upload165_entry")
    return dict(packets=heads,intervals=gaps,total=sum(gaps),display2572=shown[-3],
                display2576=shown[-2],display2580=shown[-1],last_OBJ_ACK=point(last_tile),
                upload=point(upload),last_DMA=point(dma[-1][1]),last_DMA_minus_deadline=dma[-1][1]["clock"]-cutoff,
                ACK=heads[-1]["ACK"][0],ACK_delta_MMC826=heads[-1]["ACK"][0]-read(ref/"joint.json")["frames"][-1]["ACK_masterclock"],
                DMA={v:[[a["value"],point(b)] for a,b in dma if b["frame"]==v and b["line"]>=225] for v in (51,52,53)})


def coupled(phase,mode,ref,cutoff):
    f=folder(phase,"844"+mode+"fixed")
    d=timing(f,ref,cutoff)
    j=read(f/"joint.json")
    assert j["passed"] and j["commits"]==6 and j["last_status"]==1 and contents(f)==contents(ref)
    assert j["firmware_SHA256"]==base.section.sha(arm(mode)/"src/obj-nes-100/firmware.stm")
    pk=packets(f)
    assert decode_oam([b for b in pk if b[8:10]==bytes((142,3))])==(ref/"colors636-910.bin").read_bytes()[512:1056]
    trace=[json.loads(x) for x in (f/"oam840.jsonl").read_text().splitlines()]
    first,seal=[r for r in trace if r["event"]=="wire"]
    assert first["section"]==4 and seal["op"]==3 and first["stores"]==seal["stores"] and first["last_store"]==seal["last_store"]
    bus=[e for e in read(f/"events.json") if e["event"]=="SPI"]
    offers=[e for e in bus if e["opcode"]=="0xe1"]
    assert len(offers)==len(pk)
    def busy(start,end):
        parts={}
        for e in bus:
            elapsed=min(end,e["clock"])-max(start,e["start"])
            if elapsed<0.5:continue
            key=e["opcode"]
            n,clocks=parts.get(key,(0,0))
            parts[key]=(n+1,clocks+elapsed)
        return {k:[n,round(c)] for k,(n,c) in parts.items()}
    ready=first["last_store"]
    w=window(f)
    for packet in d["packets"]:
        i=packet["index"]
        tx=offers[i-1]
        floor=i-4
        credited=next(r for r in trace if r["event"]=="credit" and r["new_retired"]>=floor)
        retired=next(r for r in w if r["event"]=="ack" and r["index"]==floor)
        assert retired["clock"]<=credited["clock"]<=tx["start"]<=tx["clock"]<=packet["head"][0]
        packet.update(credit_return=retired["clock"],ARM_saw_credit=round(credited["clock"]),
                      E1_start=round(tx["start"]),E1_end=round(tx["clock"]))
    first_obj=next(i for i,b in enumerate(pk) if b[:2]==bytes((7,1)) and b[8:10]==bytes((142,3)))
    end=offers[first_obj]["start"]
    if ready<end:
        cursor=ready
        gaps=[]
        for e in bus:
            if e["clock"]<=ready or e["start"]>=end:continue
            gaps.append(max(0,e["start"]-cursor))
            cursor=max(e["clock"],cursor)
        gaps.append(max(0,end-cursor))
        d["idle_before_first_OBJ_E1"]=dict(total=round(sum(gaps)),longest=round(max(gaps)))
    d.update(last_OAM_store=round(ready),store_count=first["stores"],OAM_packet_call=round(first["clock"]),
             outstanding_at_call=first["sent"]-first["retired"],SEAL_packet_call=round(seal["clock"]),
             before_OAM_wire=busy(ready,d["packets"][0]["E1_start"]),
             before_SEAL_wire=busy(seal["clock"],d["packets"][-1]["E1_start"]))
    return d


def analyze():
    out={}
    beam=read(Path("analysis/section841-results.json"))["phases"]
    for p in (1,2):
        ref=folder(p,"832base")
        cutoff=beam[str(p)]["VB52_start"]+22*1364
        real={m:coupled(p,m,ref,cutoff) for m in MODES}
        diag={}
        for m in ("oam","both","ready"):
            f=base.TEMP/f"nes-tail844-checked-{m}-p{p}"
            r=read(f/"result.json")
            assert r["passed"] and r["last_status"]==1 and r["commits"]==6
            assert not any((f/n).exists() for n in ("callback-error.txt","map-error.txt"))
            d=timing(f,ref,cutoff)
            assert [v[0] for v in d["DMA"][51]]==[64,64,64,768,16]
            if m!="oam":
                assert d["packets"][-1]["head"][0]-d["last_OBJ_ACK"][0]>=13320
                target_rows=[r for r in window(f) if r["g"]==910]
                wait=next(r for r in target_rows if r["event"]=="wait169")
                d["wait_after_VB52_entry"]=wait["clock"]-beam[str(p)]["VB52_start"]
                with (f/"seal528.csv").open() as stream:
                    final=[r for r in csv.DictReader(stream) if r["g"]=="910" and r["event"]=="dma"][-1]
                assert int(final["port"])==4 and d["last_DMA"][1]==53
                start53=int(final["clock"])-(int(final["line"])-225)*1364-int(final["h"])
                d["last_write_minus_246_in_next_full_blank"]=d["last_DMA"][0]-(start53+22*1364)
            diag[m]=d
        for m in MODES[1:]:
            real[m]["opening"]=opening(folder(p,f"844{m}opening",True),folder(p,"823826",True))
        out[p]=dict(deadline=cutoff,coupled=real,receiver_only=diag)
    guards={}
    for m in MODES[1:]:
        f=arm(m)/"src/obj-nes-100/firmware.stm"
        menu=read(OUT/f"menu-{m}.json")
        recover=read(OUT/f"base-{m}/result.json")
        assert menu["firmware"]==recover["firmware_sha256"]==base.section.sha(f)
        assert menu["rows"]["normal"]["released"] and recover["safe_return"] and recover["base_restored"]
        guards[m]=dict(flash_bytes=f.stat().st_size,menu_and_base=True)
        for fault in ("stop","damage"):
            d=folder(1,f"844{m}{fault}")
            start=int((d/"stop841.txt").read_text())
            end=int((d/"cancel841.txt").read_text())
            rows=window(d)
            assert end>=start and [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910))
            assert not any(r["event"] in ("ppu_dma","ppu_last","reveal") and r["clock"]>=start for r in rows)
            guards[m][fault]=[start,end]
    return dict(phases=out,guards=guards,scope="Receiver-only arrivals isolate service; ready charges final store and E1 wire duration, not concurrent ARM or shared SPI ownership. Linked M4/65816 trials include modeled shared SPI, IRQ and ROM slots; 837 receiver through 2576 then 841. No board trial.")


if __name__=="__main__":
    Path("analysis/tail844-results.json").write_text(json.dumps(analyze(),indent=2)+"\n",newline="\n")
