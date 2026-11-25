"""Run the linked 60s ARM gates and feed it pages observed on the board SPI interface."""
import argparse
import hashlib
import struct
import tempfile
from pathlib import Path
from check_nes_display1010_arm import (TimedProbe, UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, verify, timer_cases, save, check, check_game_path, empty_next_offer, loader, checked)
from prepare_nes_supply1016_arm import WORK, SRC
from read_nes_supply1016 import META, SIZE, decode, events, compare
from collections import Counter

def normal(game):
    out=WORK/"proof";out.mkdir(exist_ok=True)
    verify(1016,SRC,out,marker_values=(4,8,16,24))
    save(out/"timer.json",timer_cases(SRC))
    save(out/"menu.json",check(SRC,"1016"))
    cases,ram,entry=check_game_path(SRC,order=empty_next_offer)
    save(out/"sram.json",dict(cases=cases,ram=ram,entry=entry))
    loader(game,SRC,1016,out)
    recovery=Path(tempfile.mkdtemp(prefix="base-",dir=out))/"base"
    checked("check_nes_transfer512_recovery.py",["--arm",SRC,"--trial",1016,"--fault","none","--out",recovery],out/"base.log")
    (out/"base-result.json").write_bytes((recovery/"result.json").read_bytes())

def read_pages(path):
    result={}
    for line in path.read_text().splitlines():
        # Unwritten addresses after the terminator and the unused fourth
        # metadata word are don't-care. Reject unknowns anywhere consumed.
        raw="00"+line.strip().lower()
        p=int(raw[60:62],16)
        if p==128:
            if "x" in raw[:40]+raw[48:]:raise ValueError("undefined metadata")
        result[p]=raw
    return result

def replay(pages,case):
    m=TimedProbe(SRC);m.call("nes_budget210_reset",[])
    cache=m.data["ptrcache"];at=cache+16; gen=1384
    r=bytearray(60);struct.pack_into("<3H",r,0,5968,gen,521);r[12:16]=bytes((17,23,3,0))
    struct.pack_into("<BBHHHI",r,48,1,1,64,480,gen,202)
    if case=="different-scene":r[12]=16
    m.u.mem_write(at,bytes(r));m.u.mem_write(cache+6,struct.pack("<H",1))
    seen=[]
    def spi(cpu,pc,size,user):
        tx=cpu.reg_read(UC_ARM_REG_R1); assert 0x20000000<=tx<0x20010000
        command,p=cpu.mem_read(tx,2); assert command==0x78 and cpu.reg_read(UC_ARM_REG_R3)==32
        seen.append(p);raw=pages[p]
        b=bytearray.fromhex(raw.replace("x","0"))
        if p==2:
            if case=="bad-token":b[4]^=1
            if case=="stale":b[2]^=1
            if case=="STOP":b[31]=0
            if case=="wrong-page":b[30]=0
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),bytes(b))
        m.ret(cpu,int(not(p==2 and case=="partial")))
    pc=m.syms["nes_native165_bulk"];m.u.hook_add(UC_HOOK_CODE,spi,None,begin=pc,end=pc)
    m.u.mem_write(m.data["pending950"],struct.pack("<I",at))
    m.call("finish_header950",[])
    report=decode(bytes(m.u.mem_read(cache,SIZE)))
    if case=="normal":
        z=report["detail"];assert len(z["tiles"])==15 and [x["bytes"] for x in z["chunks"]]==[64,288,64]
        for i,t in enumerate(z["tiles"]):
            v,=t["reads"];assert v["tag"]==t["tag"]==100+i and v["row"]==3
            assert v["source"]==("demand_ROM","capture_cache","row_cache")[i%3]
            assert v["prefetch_overlap_seen"]==(i%3==0)
        # Verify every consumed word, including its sentinel, was defined in RTL.
        for p in seen[1:]:
            payload=pages[p][16:48]
            if p==seen[-1]:
                known=payload.index("000000ff")+8
                payload=payload[:known]
            assert "x" not in payload
        return z
    assert "detail" not in report
    assert seen==([128] if case=="different-scene" else [128,0,1,2])
    return seen

def wire(folder):
    fast,slow=(read_pages(folder/name) for name in ("fast-pages.hex","slow-pages.hex"))
    cases={c:replay(fast,c) for c in ("bad-token","stale","STOP","wrong-page","partial","different-scene")}
    a,b=(replay(p,"normal") for p in (fast,slow))
    first=a["tiles"][3]["reads"][0];second=b["tiles"][3]["reads"][0]
    assert second["prefetch_overlap_ticks"]-first["prefetch_overlap_ticks"]==2
    assert second["first_grant"]-first["first_grant"]==2
    (WORK/"proof").mkdir(exist_ok=True)
    delta=compare({"detail":a},{"detail":b})
    assert delta["comparable"] and delta["first_different_operand_event"]["tile"]==3
    assert not compare({},{"detail":b})["comparable"]
    physical_words=[int(line,16) for line in (folder/"source-words.hex").read_text().splitlines()]
    actual=events(physical_words,1384)
    hits=Counter(read["source"] for tile in actual for read in tile["reads"])
    assert hits==dict(capture_cache=16,row_cache=56,demand_ROM=56)
    assert "grants=56" in (folder/"source-sim.log").read_text()
    save(WORK/"proof/wire.json",dict(fast=a,slow=b,rejected=cases,actual_source_counts=hits,
        actual_output_bytes=480,firmware_sha256=hashlib.sha256((SRC/"obj-nes-100/firmware.stm").read_bytes()).hexdigest()))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("normal","wire"));p.add_argument("path",type=Path)
    a=p.parse_args();(normal if a.action=="normal" else wire)(a.path)
