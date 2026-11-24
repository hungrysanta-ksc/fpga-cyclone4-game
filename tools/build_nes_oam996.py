"""Build the 978 ARM and a WRAM-checking 65816 for a single OAM-tail receipt."""
from pathlib import Path
import json
import shutil
from unittest.mock import patch
import boot_nes_column854 as boot
from build_nes_trace_replay import Code
from nes_blank959 import ORIGIN, LOADER_SOURCE
from nes_hdma990 import BASE, PACKED
from nes_raw506 import once

WORK = BASE.parent/"nes-oam996"
ROM = WORK/"rom"


def arm():
    link=WORK/"link"
    shutil.copytree(BASE/"link",link)
    f=link/"src/nes_native_sink165.h"
    s=f.read_text();start=s.index("struct nes_native_sink165 {");end=s.index("};",start)
    f.write_text(s[:end]+" uint8_t hidden996[2];\n"+s[end:],newline="\n")
    f=link/"src/nes_native_sink165.c";s=f.read_text()
    s=once(s,"maps869.keep=0;s->column_epoch","s->hidden996[0]=s->hidden996[1]=0;maps869.keep=0;s->column_epoch")
    s=once(s,"bool same=same635","uint8_t pending996=0;\n bool same=same635")
    s=once(s,"oam227(struct nes_native_sink165 *s,const uint8_t *b)","oam227(struct nes_native_sink165 *s,const uint8_t *b,unsigned bank,uint8_t *next)")
    s=once(s,"oam227(s,p->oam)","oam227(s,p->oam,r->target,&pending996)")
    s=once(s,"s->ack635[bank]=s->serial;","s->hidden996[bank]=pending996;\n s->ack635[bank]=s->serial;")
    s=once(s," return packet_wire(s,8,4,first,b+first,4,length)",''' /* A committed marker describes only this fixed hidden sprite and zero high bits. */
 if(b[508]==0 && b[509]==0xf0 && !b[510] && !b[511] && !b[512] && !memcmp(b+512,b+513,31)){
  unsigned previous=s->hidden996[bank];
  *next=(uint8_t)(1+first/4);
  if(previous && s->displayed && s->serial>2){
   unsigned cut=(previous-1)*4;
   if(cut<first)cut=first;
   uint8_t body[6]={0,0xf0,0,0,(uint8_t)cut,(uint8_t)(cut>>8)};
   return packet_wire(s,8,4,first,body,6,544-first);
  }
 }
 return packet_wire(s,8,4,first,b+first,4,length)''')
    s=once(s,"if(op==8&&(!data||section!=4||n!=4",'''if(op==8 && n==6){
  if(!data || section!=4 || (at&3) || at>508 || expanded!=544-at)return fail(s,1);
 }else if(op==8&&(!data||section!=4||n!=4''')
    f.write_text(s,newline="\n")


def client(grouped=False):
    labels=json.loads((PACKED/"labels.json").read_bytes())
    body=bytearray((PACKED/"body.bin").read_bytes())
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    def imm(op,v):c.emit(op);c.word(v)
    def check(branch):
        c.emit(branch,3);c.jump("bad_packet")
    def service():
        c.absolute(0x20,labels["service"] & 65535);c.emit(0xf0,3);c.jump("stop_packet")
    def hook(pc,old,to):
        i=pc-ORIGIN;assert body[i:i+3]==bytes.fromhex(old)
        body[i:i+3]=bytes([0x4c])+(c.labels[to]&65535).to_bytes(2,"little")
    pc=labels["repeat227"]
    c.label("header996");c.absolute(0xad,0x120c);imm(0xc9,6);c.branch(0xf0,"check996")
    c.absolute(0x4c,(pc+3)&65535)
    c.label("check996")
    c.absolute(0xad,0x1200);imm(0xc9,0x0408);check(0xf0)
    c.absolute(0xad,0x1206);c.branch(0xd0,"warm996")
    c.absolute(0xad,0x1204);imm(0xc9,3);check(0xb0)
    c.label("warm996")
    c.long(0xaf,0x400010);imm(0xc9,0xf000);check(0xf0)
    c.long(0xaf,0x400012);check(0xf0)
    c.long(0xaf,0x400014);imm(0xc9,513);check(0x90)
    c.absolute(0xcd,0x120a);check(0xb0);c.absolute(0x0d,0x120a);imm(0x89,3);check(0xf0)
    c.absolute(0xad,0x120a);imm(0xc9,509);check(0x90)
    c.emit(0x18);c.absolute(0x6d,0x120e);check(0x90);imm(0xc9,544);check(0xf0)
    c.absolute(0xad,0x120e);c.absolute(0x8d,0x120c);c.jump("data")
    hook(pc,"ad0c12","header996")
    # Common identity, contiguous section cursor, legal extent, mark212 and
    # destination selection have completed. The two formats end at 512 and 544.
    c.label("address996");c.absolute(0x8d,0x2181);c.emit(0x85,0x7a)
    c.absolute(0xad,0x1200);imm(0xc9,0x0408);c.branch(0xd0,"old996")
    c.absolute(0xad,0x1088);imm(0xc9,544);c.branch(0xf0,"verify996")
    c.label("old996");c.absolute(0x4c,0x251d)
    c.label("verify996");service()
    # DP $60 = absolute end of the changed prefix; $7a = its first byte.
    c.long(0xaf,0x400014);c.emit(0x18);c.absolute(0x6d,0x1020);imm(0x69,0x6200);c.emit(0x85,0x60)
    c.absolute(0xad,0x1020);c.emit(0x18);imm(0x69,0x6400);c.emit(0xaa)
    c.long(0xbf,0x7f0000)
    for i in range(2,32,2):c.long(0x1f,0x7f0000+i)
    check(0xf0)
    if grouped:
        # Verify eight hidden sprites per iteration. All 32 bytes are compared,
        # including every nonzero Y word. STOP retains priority between chunks.
        c.label("groups996");c.emit(0x8a,0x38,0xe5,0x60);imm(0xc9,32);c.branch(0x90,"tail996")
        c.emit(0x8a,0x38);imm(0xe9,32);c.emit(0xaa)
        imm(0xa9,0xf000)
        for i in range(0,32,4):
            c.long(0xdf,0x7f0000+i);c.branch(0xd0,"mismatch996")
        c.long(0xbf,0x7f0002)
        for i in range(6,32,4):c.long(0x1f,0x7f0000+i)
        c.branch(0xd0,"mismatch996");service();c.branch(0x80,"groups996")
        c.label("mismatch996");c.jump("bad_packet")
    c.label("tail996");c.emit(0xe4,0x60);c.branch(0xf0,"patch996")
    c.emit(0xca,0xca,0xca,0xca)
    c.long(0xbf,0x7f0000);imm(0xc9,0xf000);check(0xf0)
    c.long(0xbf,0x7f0002);check(0xf0)
    c.emit(0x8a);imm(0x29,31);c.branch(0xd0,"tail996");service();c.branch(0x80,"tail996")
    c.label("patch996");c.emit(0xe4,0x7a);c.branch(0xf0,"done996")
    c.emit(0xca,0xca,0xca,0xca);imm(0xa9,0xf000);c.long(0x9f,0x7f0000)
    imm(0xa9,0);c.long(0x9f,0x7f0002)
    c.emit(0x8a);imm(0x29,31);c.branch(0xd0,"patch996");service();c.branch(0x80,"patch996")
    c.label("done996");service();c.jump("accepted")
    hook(0x7e2518,"8d8121","address996")
    body.extend(c.finish())
    with patch.object(boot,"STORED",6000):
        boot.build(LOADER_SOURCE,(WORK/"grouped" if grouped else ROM),bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


if __name__=="__main__":
    import sys
    if sys.argv[1:]==["grouped"]:client(True)
    else:arm();client()
