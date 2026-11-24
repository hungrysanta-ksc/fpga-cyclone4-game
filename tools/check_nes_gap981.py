"""Check slot ownership, wire order, bank returns and the same two display timelines."""
import argparse
import json
import re
from pathlib import Path

from analyze_nes_chr951 import logtext
from check_nes_bg976 import same_trace
from check_nes_game478 import next_y
from check_nes_head980 import measure
from check_nes_menu533 import check as check_menu
from check_nes_plan975 import directory, FAULTS, milliseconds, read, sha
from nes_gap981 import baseline, work


def fragments(temp):
    # Expand the captured OBJ and raster records and resolve the same visible
    # fine-row mask for each palette epoch. This identifies which source
    # fragments can actually produce the observed keys.
    objects, raster = [], []
    streams = {2:objects,4:raster}
    for packet in read(temp/"nes-gap904/data-obj/obj/frame911/packets.json"):
        data=bytes.fromhex(packet)
        at=0
        while at<len(data):
            key=int.from_bytes(data[at:at+2],"big")
            kind,index=key>>13,key&8191
            size=8 if kind==0 and index&4096 else (2,1,7,4,7,1,2,8)[kind]
            assert at+4+size<=len(data)
            value=int.from_bytes(data[at+4:at+4+size],"big")
            at+=4+size
            if kind in streams:
                assert len(streams[kind])==index
                streams[kind].append(value)
            elif kind==7 and index>>8 in (10,12):
                streams[index>>8&7].extend([value]*((index&255)+1))
            elif kind==7 and index>>8==28:
                for _ in range((index&255)+1):
                    raster.append(value)
                    value=next_y(value)
    assert (len(objects),len(raster))==(44,224)
    plans=read(temp/"nes-gap904/data-obj/obj/frame911/plans.json")
    keys={(int.from_bytes(q[4:6],"little"),q[7]):int.from_bytes(q[2:4],"little")
          for _,h in plans for q in [bytes.fromhex(h)] if q[6]==1}
    out=[]
    for index,v in enumerate(objects):
        top=v>>13&511
        if top>=256:top-=512
        masks=[0,0]
        for f in range(8):
            if v>>(38+f)&1:
                y=top+(7-f if v>>37&1 else f)
                assert 0<=y<224
                row=raster[y]
                if not row>>49&1 and row>>40&1:
                    masks[row>>44&31]|=1<<f
        for mask in masks:
            slot=keys.get((v&8191,mask))
            if slot in (86,89):
                out.append(dict(index=index,rank=v>>46&7,slot=slot,tag=v&8191,mask=mask))
    assert {r["slot"] for r in out}=={86,89}
    return out


def chain(folder):
    result=[]
    for gen in range(905,912):
        d=folder/f"gen{gen}"
        log=d/"chain981.log"
        s=logtext(log)
        row=dict(g=gen,log_sha256=sha(log),passed="PASS914 trace" in s and "Errors: 0" in s)
        result.append(row)
        if not row["passed"]:
            fault=re.search(r'(?:Fatal|Error): ([^\r\n]+)',s)
            assert fault, f"incomplete chain {log}"
            row["failure"]=fault[1]
            break
        n,diff=re.search(r'E8914 compared=(\d+) different=(\d+)',s).groups()
        row.update(polls=int(n),differences=int(diff))
        if gen==911:
            origin=int((d/"origin914.txt").read_text())
            row["publications"]=[(int(token),int(size),int(tick)+origin) for token,size,tick in
                                 re.findall(r'PUB914 token=(\d+) bytes=(\d+) at=(\d+)',s)]
            assert [size for _,size,_ in row["publications"]]==[16,32,384]
            row["batch_accepts"]=[origin+int(tick) for tick in re.findall(r'ACCEPT954 batch=\d+ edge=(\d+)',s)]
            assert len(row["batch_accepts"])==len((folder/"e9wire914-911.jsonl").read_text().splitlines())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    report=dict(fragments=fragments(a.temp),phases={},flash={},guards={})
    for phase in (1,2):
        ref=directory(a.temp,phase,"978returned","cold")
        data=report["phases"][phase]={}
        for mode in ("profile","pair","ready","rank","rankpair"):
            d=directory(a.temp,phase,"981"+mode,"cold")
            if mode=="profile":same_trace(d,ref)
            r=data[mode]=measure(d,ref)
            image,=((baseline("returned") if mode=="profile" else work(mode))/"link").rglob("firmware.stm")
            assert sha(image)==r["firmware_sha256"]
            report["flash"][mode]=image.stat().st_size
            r["slots_ms"]={slot:milliseconds(clock-r["planner"]) for clock,slot,kind,mask in read(d/"slots981.json") if kind==1}
            ledger=dict(read(d/"returns904.json"))
            tiles=[t for t in map(json.loads,(d/"producer.jsonl").read_text().splitlines()) if t["generation"]==911]
            assert [(t["kind"],t["bytes"]) for t in tiles]==[(0,16),(1,32),(1,384)]
            r["return_clock"]=[ledger[t["token"]] for t in tiles]
            r["return_delta_ms"]=[milliseconds(x-y) for x,y in zip(r["return_clock"],data["profile"]["return_clock"],strict=True)]
            r["ACK_delta_ms"]=milliseconds(r["ACK912"]-data["profile"]["ACK912"])
            r["E9_slots"]=[]
            for batch in read(d/"e9931.json"):
                if batch["g"]==911:
                    r["E9_slots"].append([int.from_bytes(w[3:5],"little") if w[0]==0x81 else hex(w[0])
                                           for rec in batch["records"] for w in [bytes.fromhex(rec)]])
            if mode in ("pair","rankpair"):
                assert r["E9_slots"]==[["0x82",86,89],[*range(90,101),"0x83"]]
            if mode in ("profile","pair"):
                r["RTL_chain"]=chain(d)
    for mode in ("pair","ready","rank","rankpair"):
        ok=report["guards"][mode]={}
        for fault,status in FAULTS.items():
            d=a.temp/f"nes-981{mode}-{fault}"
            result=read(d/"result.json")
            assert result["passed"] and result["commits"]==6 and result["last_status"]==status
            assert sha(d/"retained.rgb")==sha(directory(a.temp,1,"981"+mode,"cold")/"frame-910.rgb")
            ok[fault]=status
        ok["normal_menu_release"]=check_menu(work(mode)/"link/src","966")["rows"]["normal"]["released"]
        assert ok["normal_menu_release"]
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
