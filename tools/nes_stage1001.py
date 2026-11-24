"""Measure packet-side checks, dedicated final DMA channels and fresh group setup."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_dma1000 as previous
from build_nes_trace_replay import Code
from check_nes_output970 import packet_path, replay
from nes_dma1000 import ORIGIN, PACKED, once


def candidate(fresh,table=False,*,taps=None):
    labels=json.loads((PACKED/"labels.json").read_bytes())
    body=(PACKED/"body.bin").read_bytes()
    c=Code(ORIGIN+len(body))
    c.labels.update(labels)
    writes={}
    def entry(name,old,opcode):
        addr=labels[name]
        assert body[addr-ORIGIN:addr-ORIGIN+3]==bytes.fromhex(old)
        ptr=c.base+len(c.data)
        writes[addr]=bytes((opcode,ptr&255,ptr>>8&255))
    def imm(n):
        c.emit(0xa9); c.word(n)
    def load(a):
        c.absolute(0xad,a)
    def store(a):
        c.absolute(0x8d,a)
    # BEGIN has selected the inactive bank. Channels 4/5 are outside both
    # the tile DMA and all HDMA masks. Programming them cannot start DMA.
    entry("valid_a212","8d 54 12",0x20)
    store(0x1254)
    for channel,port,offset,length in ((0x4340,0x2202,0x6000,512),(0x4350,0x0400,0x6200,544)):
        imm(port);store(channel)
        load(0x1020);c.emit(0x18,0x69);c.word(offset);store(channel+2)
        imm(0x7f);store(channel+4)
        imm(length);store(channel+5)
    c.emit(0x60)

    # Keep the successful final service/beam gate. Only its two final DMA jobs
    # use channels 4/5. The short-palette/OAM command changes both sizes.
    entry("final_upload212_same_blank212","e2 20 a9",0x4c)
    load(0x14d8);c.branch(0xf0,"full")
    imm(2);store(0x4345);imm(112);store(0x4355)
    c.label("full");c.emit(0xe2,0x20)
    for addr in (0x420c,0x2121,0x2102,0x2103):
        c.absolute(0x9c,addr)
    c.store(0x420b,16);c.store(0x420b,32)
    c.jump("final_upload212_scroll")

    # Final list construction now has no consumer, except its counter reset.
    # Preserve the original raw validator, STOP check and group formation.
    start=labels["no_raw212"]+3
    end=labels["group538"]-11
    assert body[end-ORIGIN:end-ORIGIN+3]==bytes.fromhex("20 10 34")
    writes[start]=bytes((0x4c,end&255,end>>8&255))
    # At group entry, preprogram the first ordinary descriptor before the
    # serviced beam wait. Raw uses a different addressing mode and falls back.
    base=labels["prepare665"]
    site=ORIGIN+body.index(bytes.fromhex("20 ec 38"),base-ORIGIN,base-ORIGIN+30)
    ptr=c.base+len(c.data)
    writes[site]=bytes((0x4c,ptr&255,ptr>>8&255))
    c.long(0xbf,0x7e4002);c.emit(0xc9,0,0x50);c.branch(0xf0,"regular_wait")
    c.emit(0xc9,0,0x90);c.branch(0xf0,"regular_wait")
    c.emit(0x4a);store(0x2116)
    c.long(0xbf,0x7e4000);store(0x4302)
    c.long(0xbf,0x7e4004);store(0x4305)
    wait=labels["wait169" if fresh else "group_wait912"]&65535
    c.absolute(0x20,wait);c.branch(0x90,"cancel")
    c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20);c.jump("raw_advance489")
    c.label("cancel");c.jump("upload_return212")
    c.label("regular_wait");c.absolute(0x20,wait);c.absolute(0x4c,(site+3)&65535)
    writes[c.base]=c.finish()
    if table:
        from nes_table1001 import attach
        extra=attach(writes,labels,body)
        if taps is not None:
            taps.update({k:extra[k] for k in ("admitted","proof_hit","fallback","snapshot","compare","mismatch")})
    return writes


def observe(lua, mode):
    fresh=mode in ("fresh","tablefresh")
    lua=previous_instrument(lua,"fresh" if fresh else "control")
    # The fresh control sets prepare665's wait operand at SEAL; use the same
    # stock fresh group and let our trampoline call that wait explicitly.
    if fresh:
        base=json.loads((PACKED/"labels.json").read_bytes())["prepare665"]
        body=(PACKED/"body.bin").read_bytes()
        site=ORIGIN+body.index(bytes.fromhex("20 ec 38"),base-ORIGIN,base-ORIGIN+30)
        for i,v in enumerate((0x68,0x2d),1):
            lua=once(lua,f"emu.write({site+i-0x7e0000},{v},emu.memType.snesWorkRam)","do end")
    anchor='packet=requests[index];sample516("load");'
    taps={}
    writes=candidate(fresh,mode.startswith("table"),taps=taps)
    if taps:
        labels=json.loads((PACKED/"labels.json").read_bytes())
        taps.update({k:labels[k] for k in ("accepted","table181","coverage212","compact489","upload165_entry","group538","reply","validate181")})
        target="checkedMem527(function()sample516('validate181')end,emu.callbackType.exec,8269746)"
        taplua="\n".join(f"checkedMem527(function() if packet and pw(8)==912 then sample516('p1001_{name}',word(0x3f80)) end end,emu.callbackType.exec,{address})" for name,address in taps.items())
        lua=once(lua,target,target+"\n"+taplua)
    if mode in ("tablecorrupt","tablecoverage"):
        # The inherited negative harness flips generation. Restore that byte
        # before the receiver sees it and inject exactly one different fault.
        hook="packet=requests[index];"
        fault='local at=0x10000+word(0x1020)+0x6a21+83;emu.write(at,rd(at)~1,emu.memType.snesWorkRam)' if mode=="tablecorrupt" else 'packet=packet:sub(1,40)..string.rep(string.char(255),144)..packet:sub(185)'
        injector="if pb(0)==3 and pw(8)==913 then packet=packet:sub(1,8)..string.char(144)..packet:sub(10);"+fault+" end;"
        lua=once(lua,anchor,anchor+injector)
    patchcode=";".join(f"emu.write({pc+i-0x7e0000},{v},emu.memType.snesWorkRam)"
                       for pc,blob in writes.items() for i,v in enumerate(blob))
    lua=once(lua,anchor,anchor+"if pw(8)==912 and pb(0)==1 then "+patchcode+" end;")
    # Count every physical CGRAM/OAM byte using the real channel configuration.
    lua=once(lua,"{0x4300,0x4306}","{0x4300,0x4306},{0x4340,0x4356}")
    lua=once(lua,"local function write(a,v)","""local extra1001={}
local function write(a,v)
 if a>=0x4340 and a<=0x4356 then extra1001[a]=v end
 if a==0x420b and (v==16 or v==32) then
  local base=v==16 and 0x4340 or 0x4350
  assert(packet and pb(0)==3 and pw(8)==912 and dmaRemaining==0)
  local n=word(0x14d8)==0 and (v==16 and 512 or 544) or (v==16 and 2 or 112)
  assert(extra1001[base+1]==(v==16 and 0x22 or 4) and extra1001[base+4]==127)
  assert(extra1001[base+2]+256*extra1001[base+3]==word(0x1020)+(v==16 and 0x6000 or 0x6200))
  assert(extra1001[base+5]+256*extra1001[base+6]==n)
  dmaLength=n;dmaRemaining=n;sample516('ppu_dma',n)
 end""")
    return lua


previous_instrument=previous.instrument


def run(temp,phase,mode,fault=None):
    if mode in ("recorded","tablerecorded"):
        src=previous.directory(temp,phase,"978returned","cold")
        commands,_=packet_path(src,912,expected_shape=(21,8))
        return replay(temp,src,temp/f"nes-stage1001-{mode}-p{phase}","fixed",commands,912,
                      observe=lambda lua:observe(lua,mode))
    with patch.object(previous,"instrument",lambda lua,_:observe(lua,mode)):
        previous.run(temp,phase,"1001"+mode,fault=fault,earliest_begin=(mode in ("begin","tablebegin")))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("paid","fresh","recorded","begin","table","tablefresh","tablerecorded","tablebegin","tablecorrupt","tablecoverage"))
    p.add_argument("--fault",choices=("bad_seal","stop_raw"))
    a=p.parse_args();run(a.temp.resolve(),a.phase,a.mode,a.fault)
