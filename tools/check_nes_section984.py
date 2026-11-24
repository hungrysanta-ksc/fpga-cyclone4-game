"""Compare canonical section bytes and inject faults inside the compact transfer."""
import argparse
import json
from pathlib import Path

from check_nes_output970 import packet_path, replay
from check_nes_plan975 import directory, sha
from nes_raw506 import once
from nes_section984 import WORK


def verify(temp,phase,fault):
    folder=directory(temp,phase,"984compact","cold")
    ref=directory(temp,phase,"978returned","cold")
    commands,_=packet_path(folder,911,expected_shape=(15,3))
    originals,_=packet_path(ref,911)
    raw={}
    for g,op,_,wire,*_ in originals:
        b=bytes.fromhex(wire)
        if op==2 and b[1]==5:
            raw[g,int.from_bytes(b[10:12],"little")]=b[16:]
    table={}
    for g,op,_,wire,*_ in commands:
        b=bytes.fromhex(wire)
        if b[:2]!=bytes((9,5)):
            continue
        src=raw[g,1121]+raw[g,1322]
        packed=b[16:]
        decoded=b"".join(packed[i:i+2]*32 for i in (6,8,10))
        decoded+=b"".join(packed[i:i+21]+bytes(60) for i in (12,33,54))+packed[:6]
        assert len(packed)==75 and decoded==src and len(src)==441
        table[g]=src.hex()
    assert 911 in table
    out=temp/f"nes-984check2-{phase}-{fault}"
    labels=json.loads((WORK/"client/labels.json").read_bytes())

    def observe(lua):
        values=",".join(f"[{g}]='{s}'" for g,s in table.items())
        lua=once(lua,"local function sample516(event,value)",f"""
local expected984={{{values}}}
local injected984=false
local function sample516(event,value)""")
        lua=once(lua,"lastStatus=ack[1];sample516","""if pb(0)==9 and pb(1)==5 and ack[1]==0 then
   local original=assert(expected984[pw(8)])
   if pw(8)>905 then assert(word(0x1034)~=word(0x1032)) end
   local dest=0x10000+word(0x1020)+0x6500+1121
   for i=0,440 do assert(rd(dest+i)==tonumber(original:sub(2*i+1,2*i+2),16),'section984 WRAM '..i) end
  end
  lastStatus=ack[1];sample516""")
        if fault in ("partial","damage"):
            pc=labels["raw984_0_check"]
            action=("injected984=true" if fault=="partial" else
                    "local a=0x10000+word(0x1020)+0x6500+1121; emu.write(a,(rd(a)+1)%256,emu.memType.snesWorkRam); injected984=true")
            lua=once(lua,"local function sample516(event,value)",f"""
emu.addMemoryCallback(function()
 if not injected984 and packet and pw(8)==911 then {action} end
end,emu.callbackType.exec,{pc})
local function sample516(event,value)""")
            if fault=="partial":
                lua=once(lua,"if a==0x6001 then","if a==0x6001 then\n  if injected984 then return 128 end")
            lua=once(lua,"if rejected then","if rejected then assert(injected984,'missing compact injection') end\n  if rejected then")
        return lua

    mode={"normal":None,"partial":"stop_decode","damage":"bad_seal","seal":"bad_seal"}[fault]
    replay(temp,folder,out,"control",commands,911,mode,observe=observe)
    r=json.loads((out/"result.json").read_bytes())
    assert r["passed"]
    if mode:
        assert r["commits"]==6 and r["last_status"]==(228 if fault=="partial" else 224)
        assert sha(out/"retained.rgb")==sha(ref/"frame-910.rgb")
    print(fault,r["commits"],r["last_status"])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("fault",choices=("normal","partial","damage","seal"))
    a=p.parse_args()
    verify(a.temp,a.phase,a.fault)
