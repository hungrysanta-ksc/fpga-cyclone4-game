"""Measure 911 raw ownership and move three already received VRAM rows into VBlank."""
import argparse
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import boot_nes_column854 as boot
import nes_page963
import nes_proof989
from build_nes_trace_replay import Code
from check_nes_plan975 import read
from nes_blank959 import LOADER_SOURCE, ORIGIN
from nes_hdma990 import BASE, PACKED
from nes_tile985 import work as tile_work
from nes_raw506 import once

ROOT = BASE.parent/"nes-raw991"
ROM = ROOT/"rom"
FLAG = 0x1800  # cleared at BEGIN and common invalidation; 1 armed, 2 uploaded


def receiver():
    labels = read(PACKED/"labels.json")
    body = bytearray((PACKED/"body.bin").read_bytes())
    c = Code(ORIGIN+len(body))
    c.labels.update(labels)
    def imm(op,value):
        c.emit(op); c.word(value)
    def hook(label,old,entry,op=0x4c):
        i=labels[label]-ORIGIN
        assert body[i:i+3]==bytes.fromhex(old)
        body[i:i+3]=bytes((op,))+(c.labels[entry]&65535).to_bytes(2,"little")
    def require(branch,label):
        c.emit(branch,3);c.jump(label)
    def eq(addr,val,label):
        c.absolute(0xad,addr);imm(0xc9,val);require(0xf0,label)
    def resume(label):
        c.absolute(0x4c,(labels[label]+3)&65535)

    for name,addr in (("begin",0x14d8),("invalidate635",0x14d0)):
        c.label(name+"991");c.absolute(0x9c,FLAG);c.absolute(0x9c,addr);resume(name)
        hook(name,"9c"+addr.to_bytes(2,"little").hex(),name+"991")

    c.label("accepted991");c.absolute(0xad,FLAG)
    c.branch(0xd0,"armed991")
    eq(0x1200,0x0502,"done991");eq(0x120a,1121,"done991");eq(0x120c,201,"done991")
    eq(0x108a,1322,"done991") # contiguous, including the 192 raw bytes
    c.absolute(0xad,0x1034);c.absolute(0xcd,0x1032);require(0xd0,"done991")
    c.emit(0xaa,0xe2,0x20);c.absolute(0xbd,0x125a);c.emit(0xc9,1,0xc2,0x20);require(0xf0,"done991")
    imm(0xa9,1);c.absolute(0x8d,FLAG)
    c.label("armed991");imm(0xc9,1);require(0xf0,"done991")
    c.emit(0xe2,0x20);c.absolute(0x20,0) # forward call to the bounded beam check
    beam_call=len(c.data)-2
    c.emit(0xc2,0x20);require(0x90,"done991")
    c.absolute(0xad,0x1020);c.emit(0x18);imm(0x69,0x6961);c.absolute(0x8d,0x4302)
    imm(0xa9,0x7f);c.absolute(0x8d,0x4304);imm(0xa9,0x1801);c.absolute(0x8d,0x4300)
    c.emit(0xe2,0x20);c.store(0x2115,0x81);c.emit(0xc2,0x20)
    c.absolute(0xad,0x1034);c.branch(0xf0,"bankA991");imm(0xa9,0x4800);c.branch(0x80,"dest991")
    c.label("bankA991");imm(0xa9,0x2800)
    c.label("dest991");c.emit(0xaa)
    for plane in range(3):
        c.emit(0xe2,0x20);c.absolute(0xad,0x6001);c.emit(0x89,0x80,0xc2,0x20);require(0xf0,"stop991")
        c.absolute(0x8e,0x2116);imm(0xa9,64);c.absolute(0x8d,0x4305)
        c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
        if plane<2:
            c.emit(0x8a,0x18);imm(0x69,8);c.emit(0xaa)
    imm(0xa9,2);c.absolute(0x8d,FLAG);c.emit(0xe2,0x20);c.store(0x2115,0x80);c.emit(0xc2,0x20)
    c.label("done991");c.absolute(0xad,0x1200);resume("accepted")
    hook("accepted","ad0012","accepted991")
    c.label("stop991");c.emit(0xe2,0x20);c.store(0x2115,0x80);c.emit(0xc2,0x20);c.jump("stop_packet")
    c.label("beam991")
    i=labels["beam935"]-ORIGIN
    bounded=bytes(body[i:body.index(bytes.fromhex("c9fdb00218603860"),i,i+64)+8])
    assert bounded.endswith(bytes.fromhex("c9fdb00218603860"))
    c.data.extend(bounded[:-7]+bytes((234,))+bounded[-6:])
    c.data[beam_call:beam_call+2]=(c.labels["beam991"]&65535).to_bytes(2,"little")

    # Execute all existing compact/coverage/semantic checks. Skip only the
    # already executed one-row upload in the same inactive bank and generation.
    c.label("dispatch991");c.emit(0x48);eq(FLAG,2,"normal991")
    eq(0x1240,1,"normal991");eq(0x1258,192,"normal991");eq(0x125c,1,"normal991")
    c.emit(0x68,0x60)
    c.label("normal991");c.emit(0x68);c.jump("raw_dma489")
    hook("raw_dispatch489","20de31","dispatch991",0x20)
    body.extend(c.finish())
    with patch.object(boot,"STORED",5800):
        boot.build(LOADER_SOURCE,ROM,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


def prepare(both=False):
    dst=ROOT/("both" if both else "first")/"link"
    shutil.copytree(BASE/"link",dst)
    p=dst/"src/nes_native_sink165.c";s=p.read_text()
    s=once(s," bool same=same635(s,p);",""" bool first991=p->scroll_issued && !r->map_upload && p->patch_count==1;
 if(first991){
  uint8_t *head=(uint8_t *)p->bg_keys+6144;
  memcpy(head,raw,192);memcpy(head+192,p->patch.mode[0],9);
  if(!packet(s,2,5,1121,head,201))return false;
 }
 bool same=same635(s,p);""")
    s=once(s,"if(!packet(s,2,5,offset,joined,201))","if(!first991 && !packet(s,2,5,offset,joined,201))")
    if both:
        s=once(s,"  if(!packet(s,2,5,1121,head,201))return false;","""  const uint8_t *table=(const uint8_t *)p+__builtin_offsetof(struct nes_native_video165,patch.mode);
  memcpy(head+201,table+9,234);memcpy(head+435,p->patch.size,6);
  if(!packet(s,2,5,1121,head,201)||!packet(s,2,5,1322,head+201,240))return false;""")
        s=once(s,"if(!packet(s,2,5,offset+201,joined+201,240))","if(!first991 && !packet(s,2,5,offset+201,joined+201,240))")
    p.write_text(s,newline="\n")


def observe(script):
    anchor='dmaRemaining=dmaLength;sample516("ppu_dma",dmaLength)'
    extra="""if packet and rd(0x1800) == 1 and regs[0x4304]==0x7f and dmaLength==64 and pb(0)~=3 then
   local bank=word(0x1034);assert(bank~=word(0x1032) and st['ppu.scanline']>=225 and st['ppu.scanline']<=246)
   local dest=(regs[0x2116] or 0)+256*(regs[0x2117] or 0)
   local plane=(dest-(bank==0 and 0x2800 or 0x4800))/8
   assert(plane==0 or plane==1 or plane==2)
   local src=0x10000+word(0x1020)+0x6961+64*plane
   local expected=file('expected-'..pw(8)..'.bin')
   for j=0,63 do assert(rd(src+j)==expected:byte(1122+(j//2)*64+plane*16+j%2),'early raw bytes') end
   sample516('raw991',dmaLength)
  end;"""
    return once(script,anchor,'dmaRemaining=dmaLength;'+extra+'sample516("ppu_dma",dmaLength)')


def run(temp,phase,mode):
    aligned=mode=="matched"
    def launch(original):
        def popen(args,*a,**kw):
            if "--testRunner" in args:
                f=Path(args[args.index("--testRunner")+1])
                s=f.read_text(encoding="utf-8")
                if aligned:s=nes_proof989.align_boot(s)
                f.write_text(observe(s),encoding="utf-8",newline="\n")
            return original(args,*a,**kw)
        return popen
    with patch.object(nes_proof989,"ROM",ROM),patch.object(nes_page963,"PACKED",PACKED if aligned else ROM),patch.object(subprocess,"Popen",launch(subprocess.Popen)):
        nes_page963.simulate(temp,phase,"cold",True,ROOT/mode if mode in ("first","both") else tile_work("after") if mode=="drain" else BASE,True,tag="991"+mode,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("build","prepare","prepareboth","run"))
    p.add_argument("temp",type=Path,nargs="?")
    p.add_argument("phase",type=int,nargs="?",choices=(1,2))
    p.add_argument("mode",nargs="?",choices=("matched","static","first","both","drain"))
    a=p.parse_args()
    if a.action=="build":receiver()
    elif a.action.startswith("prepare"):prepare(a.action=="prepareboth")
    else:run(a.temp,a.phase,a.mode)
