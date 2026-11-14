# SPDX-License-Identifier: MIT
"""Reconcile checked row writes with actual E0/E8 traffic, packet receipt and PPU transfers."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_first780 import RANGES,coverage
from analyze_nes_tail779 import examine
from analyze_nes_grant782 import transitions
from analyze_nes_output768 import csv_groups,one,read,sha
from analyze_nes_prefix777 import ms
from analyze_nes_supply781 import measure


def analyze(folder,base):
    result=measure(folder,base)
    events=read(folder/"events.json")
    frame=[e for e in events if e.get("generation")==969]
    origin=result["ACK968"]
    since=lambda c:ms(c-origin)
    begin=one(frame,"planner_enter")["clock"]
    head=[e for e in frame if e.get("opcode")=="0xe1"]
    windows=csv_groups(folder/"window.csv")
    w=windows[969]
    dense_reveals={}
    for generation in range(951,958):
        reveal=one([r for r in windows[generation] if r["op"]==3],"reveal")
        dense_reveals[generation]={key:reveal[key] for key in ("clock","line","frame")}
    loads=[r for r in w if r["event"]=="load"]
    packets=[bytes.fromhex(json.loads(s)[2]) for s in (folder/"packets.jsonl").read_text().splitlines()]
    trace=[e for e in events if e["event"]=="SPI" and e["start"]>=begin and e.get("generation")==969]
    # An E8 repeating an immutable descriptor is still a full checked transaction.
    previous=None
    def owner(e):
        nonlocal previous
        op=e["opcode"]
        if op=="0xe0": return "E0_credit_status"
        if op!="0xe8": return op
        r=bytes.fromhex(e["reply"])
        if not r[6]: return "E8_empty"
        desc=r[6:18]
        repeat=desc==previous
        previous=desc
        return "E8_repeat" if repeat else "E8_new"
    spans=[(e["start"],e["clock"],owner(e)) for e in trace]
    def cost(left,right):
        assert left<=right
        clocks=Counter();counts=Counter()
        for lo,hi,k in spans:
            duration=min(right,hi)-max(left,lo)
            if duration>0:
                clocks[k]+=duration;counts[k]+=1
        remainder=right-left-sum(clocks.values())
        assert remainder>=-1
        return dict(ms=ms(right-left),wire_ms={k:ms(v) for k,v in clocks.items()},
                    transfers=dict(counts),outside_wire_ms=ms(remainder))
    rows={}
    expected=(folder/"map-969.bin").read_bytes()
    for off,length in ((2304,192),(2496,64)):
        payload=bytearray((folder/"map-968.bin").read_bytes()[off:off+length])
        stores=[e for e in frame if e["event"]=="map_store757" and e["clock"]>=begin and
                off<=e["offset"]<off+length]
        assert stores
        for s in stores:
            pos=s["offset"]-off
            old,new=bytes.fromhex(s["old"]),bytes.fromhex(s["new"])
            assert payload[pos:pos+len(old)]==old
            payload[pos:pos+len(new)]=new
        assert payload==expected[off:off+length]
        last=max(s["clock"] for s in stores)
        [(tx,load)]=[(tx,load) for tx,load in zip(head,loads,strict=True)
                     if packets[load["index"]-1][1]==2 and int.from_bytes(packets[load["index"]-1][10:12],"little")==off]
        enter=one([e for e in frame if e.get("offset")==off],"map_packet_enter")["clock"]
        enqueue=one([e for e in frame if e.get("offset")==off],"map_enqueue")["clock"]
        ack=one([r for r in w if r["index"]==load["index"]],"ack")
        assert last<=enter<=enqueue<=tx["start"]<=tx["clock"]<=load["clock"]+1<=ack["clock"]
        window=[e for e in trace if last<=e["start"] and e["clock"]<=tx["start"]]
        credit=[]
        for e in window:
            if e["opcode"]!="0xe0":continue
            response=bytes.fromhex(e["reply"])
            sent,retired=int.from_bytes(response[3:5],"big"),int.from_bytes(response[5:7],"big")
            credit.append(dict(end=since(e["clock"]),outstanding=(sent-retired)&65535,accepted=sent,retired=retired))
        rows[off]=dict(bytes=length,store_count=len(stores),credit=credit,
            row_last_stores=[since(max(e["clock"] for e in stores if start<=e["offset"]<start+64))
                             for start in range(off,off+length,64)],last_row_store=since(last),packet_enter=since(enter),
            on_bus=since(tx["start"]),returned=since(ack["clock"]),ACK_scanline=ack["line"],ACK_frame=ack["frame"],
            after_rows_to_enter=cost(last,enter),enter_to_enqueue=cost(enter,enqueue),
            enqueue_to_wire=cost(enqueue,tx["start"]),wire=cost(tx["start"],tx["clock"]),
            queue_after_wire_ms=ms(load["clock"]-tx["clock"]),receiver_service_ms=ms(ack["clock"]-load["clock"]))
    # Tile ownership or a queue ACK cannot count as a transferred byte.
    # measure() checks the last PPU write and the independently expected screen.
    first_events=result["first_blank_events"]
    order=[(packets[r["index"]-1][0],packets[r["index"]-1][1],
            int.from_bytes(packets[r["index"]-1][10:12],"little"),since(t["start"]))
           for t,r in zip(head,loads,strict=True)]
    return dict(rows=rows,first=result["first"],first_blank_events=first_events,E1_order=order,transfers=result["transfers"],dense_ms=result["dense_ms"],
                dense_VBlanks=result["dense_VBlanks"],dense_reveals=dense_reveals,final970=result["final970"],intervals=result["intervals"],
                first_two_tiles=result["tile_heads"][:2],input=transitions(folder),ACK968_to_970=result["ACK968_to_970"],reveal_line=result["reveal_line"],
                verified=result["verified"],firmware=result["firmware"])


def report(temp,work,names):
    out=dict(ranges=RANGES,phases={},builds={},scope="M4 and original 65816, modeled SPI/IRQ/ROM. Row clocks in ms from ACK968. Wire totals are nonoverlapping within each interval; the two rows overlap.")
    for n,i in names:
        src=work/f"arm{i:02d}/src/obj-nes-100"
        g=read(work/f"g{i}/guards.json")
        assert g["guards"]["firmware"]==sha(src/"firmware.stm")
        assert read(work/f"g{i}/padding.json")["firmware"]==g["guards"]["firmware"]
        out["builds"][n]=dict(flash=(src/"firmware.stm").stat().st_size,ELF=sha(src/"sd2snes.elf"),guards=g)
    for p in (1,2):
        base=temp/f"nes-range778-763-p{p}"
        prior=read(Path(__file__).resolve().parents[1]/"analysis/grant782.json")["phases"][str(p)]
        ph=out["phases"][p]={}
        for n in ["control"]+[n for n,i in names]:
            d=temp/f"nes-grant783-{n}-p{p}"
            r=ph[n]=analyze(d,base)
            ref=prior["763"]
            if n=="control":
                for k in ("first","dense_ms","dense_VBlanks","final970","ACK968_to_970"):
                    assert r[k]==prior["map"][k],(k,r[k],prior["map"][k])
            else:
                assert r["firmware"]==out["builds"][n]["guards"]["guards"]["firmware"]
            r["dense_delta_ms"]=round(r["dense_ms"]-ref["dense_ms"],6)
            r["final_delta_ms"]=ms(r["final970"]-ref["final970"])
            r["local_delta_ms"]=round(r["ACK968_to_970"]-ref["ACK968_to_970"],6)
            r["first_map_starts"]=[tr[-1] for tr in r["transfers"] if tr[0]=="map" and tr[4]==-1]
            r["target_map_starts"]=[tr[-1] for tr in r["transfers"] if tr[0]=="map" and tr[4]==-1 and
                any(kind=="map" and max(at,tr[1])<min(at+size,tr[1]+tr[2]) for kind,at,size in RANGES)]
            r["matches_782D_display"]=all(r["intervals"][g]<=prior["map"]["intervals"][str(g)] for g in (909,960,969))
            r["pass_all"]=bool(n!="control" and out["builds"][n]["flash"]<=212992 and
                r["matches_782D_display"] and r["intervals"][969]==2 and
                r["first"]==[length for _,_,length in RANGES] and r["target_map_starts"] and max(r["target_map_starts"])<=252 and
                r["dense_delta_ms"]<0 and r["final_delta_ms"]<0)
        src=temp/f"nes-grant783-lend-p{p}"
        fixed=temp/f"nes-rows783-idle-p{p}"
        rec=examine(src,fixed,src,fixed=True)
        assert read(fixed/"audit.json")["frames"]==66
        ph["isolated"]=dict(first=coverage(rec["transfers"],-1),transfers=rec["transfers"],
                            received=rec["intervals"],producer_retimed=False)
    out["STOP"]={}
    for n,p in (("prefix",1),("lend",1),("defer",2),("window",1)):
        proof=read(temp/f"nes-rows783-stop-{n}/proof.json")
        assert proof["retained"]==sha(temp/f"nes-grant783-{n}-p{p}/frame-968.rgb")
        assert proof["commits"]==64 and proof["blanks_after_STOP"]>=3
        out["STOP"][n]=proof
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","work","out"):p.add_argument(k,type=Path)
    p.add_argument("--candidate",action="append",nargs=2,required=True,metavar=("NAME","BUILD"))
    a=p.parse_args()
    r=report(a.temp,a.work,[(n,int(i)) for n,i in a.candidate])
    a.out.write_text(json.dumps(r,indent=2)+"\n",newline="\n")
