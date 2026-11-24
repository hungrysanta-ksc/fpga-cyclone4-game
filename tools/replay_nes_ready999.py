"""Replay unchanged receiver and SPI packets using source-write release times."""
import argparse
import json
import math
from pathlib import Path
from check_nes_plan975 import directory, packet_path, read, replay
from nes_raw506 import once


def releases(temp,phase,paired):
    tag="999pair" if paired else "999ref"
    d=directory(temp,phase,tag,"cold")
    origin=directory(temp,phase,"998pair" if paired else "978returned","cold")
    from check_nes_plan975 import sha
    for f in ("events.json","producer.jsonl","window.csv","records.bin"):
        assert sha(d/f)==sha(origin/f)
    m=read(temp/f"nes-{tag}-writes-p{phase}.json")
    last={int(k):v for k,v in m["last"].items()}
    image=bytes.fromhex(m["image"])
    cmds,ledger=packet_path(d,907)
    raw=[64*i+16*p+b for p in range(3) for i in range(32) for b in (0,1)]
    canonical=raw+list(range(2048,2291))+list(range(2292,2298))
    assert image[8704:12800]==(d/"map-906.bin").read_bytes()==(d/"map-907.bin").read_bytes()
    assert not any(i in last for i in range(8704,12800))
    jobs=[]
    for cmd,row in zip(cmds[-len(ledger):],ledger,strict=True):
        b=bytes.fromhex(cmd[3]);op,section=b[:2]
        offset=int.from_bytes(b[10:12],"little")
        physical=int.from_bytes(b[12:14],"little")
        span=int.from_bytes(b[14:16],"little") or physical
        payload=b[16:]
        assert len(payload)==physical
        if op in (1,3,7):
            # BEGIN remains fixed. Grant intrinsic SEAL fields for free,
            # after every preceding packet; tile release uses first valid E8.
            ready={1:row["issue"],3:m["entry"],7:cmd[-2]}[op]
        elif op==5:
            assert section==5 and offset==21 and payload==bytes(2)
            ready=last[13856+20]
        else:
            if section==5 and offset>=1121:
                ix=canonical[offset-1121:offset-1121+span]
            else:
                start={2:8704,3:13344,4:12800,5:13856}[section]+offset
                ix=range(start,start+span)
            expansion=(payload * ((span+physical-1)//physical))[:span]
            assert bytes(image[i] for i in ix)==expansion,(section,offset)
            ready=max(last.get(i,0) for i in ix)
        joined=ready
        if section==5 and offset>=1121:
            joined=max(m["joined"][offset-1121:offset-1121+span])
        jobs.append(dict(row,offset=offset,wire_B=len(b)+3,duration=cmd[-1],src=ready,joined=joined))
    return d,cmds,jobs


def run(t,phase,paired,mode,*,fault=None,instrumentation=None,suffix=""):
    d,cmds,jobs=releases(t,phase,paired)
    out=t/f"nes-ready999-{'pair' if paired else 'ref'}-{mode}-p{phase}"
    out=out.with_name(out.name+(("-"+fault) if fault else suffix))
    current=cmds[-len(jobs):]
    previous=cmds[:-len(jobs)]
    last={}
    order=[]
    # Maintain section coverage order and the order of tile-bank consumption.
    for i,j in enumerate(jobs[1:-1],1):
        group="tile" if j["op"]==7 else j["section"]
        at=max(last.get(group,0),j["joined" if mode=="joined" else "src"])
        last[group]=at
        order.append((at,i))
    order.sort()
    order=[(0,0),*order,(jobs[-1]["src"],len(jobs)-1)]
    stream=list(previous)
    for seq,(at,i) in enumerate(order):
        g,op,arrival,wire,bulk,_,dur=current[i]
        b=bytearray.fromhex(wire)
        assert int.from_bytes(b[2:4],"little")==i
        b[2:4]=seq.to_bytes(2,"little")
        stream.append((g,op,arrival,b.hex(),bulk,at,0 if mode=="instant" else dur))
    def observe(lua):
        if mode=="busy":
            e=read(d/"events.json")
            (out/"busy.txt").write_text("".join(f"{math.floor(r['start'])} {math.ceil(r['clock'])}\n"
                    for r in e if "start" in r and r.get("opcode")!="0xe1"))
        lua=once(lua,'if sent-retired>=4 then break end','if sent-retired>=2 then break end')
        anchor="checkedMem527(function()sample516('upload165_entry')end,emu.callbackType.exec,8268414)"
        taps="\n".join(f"checkedMem527(function()sample516('{name}')end,emu.callbackType.exec,{pc})"
                    for name,pc in (("enter_validate999",0x7e2fb2),("exit_validate999",0x7e26e1)))
        lua=once(lua,anchor,anchor+"\n"+taps)
        return instrumentation(lua) if instrumentation else lua
    return replay(t,d,out,"frame",stream,907,fault,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("instant","paid","busy","joined"));p.add_argument("--paired",action="store_true")
    p.add_argument("--guard",choices=("bad_seal","stop_decode"))
    a=p.parse_args();run(a.temp,a.phase,a.paired,a.mode,fault=a.guard)
