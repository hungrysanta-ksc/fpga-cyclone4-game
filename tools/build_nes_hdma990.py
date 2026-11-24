"""Build early and late table-first ARM producers and enforce the outstanding raw range."""
import argparse
import shutil
from unittest.mock import patch

import boot_nes_column854 as boot
from build_nes_trace_replay import Code
from check_nes_plan975 import read
from nes_blank959 import LOADER_SOURCE, ORIGIN
from nes_blank960 import PACKED
from nes_hdma990 import BASE, ROOT, ROM
from nes_raw506 import once

PENDING=0x1800


def arm(mode):
    literal_words=mode.startswith("rle")
    repeat=mode in ("repeatgap","repeatpacked","rlegap","rlepacked")
    safe=mode.startswith("safe") or repeat
    dst=ROOT/mode/"link"
    mode=mode.removeprefix("safe").removeprefix("repeat").removeprefix("rle")
    shutil.copytree(BASE/"link",dst)
    src=dst/"src"
    p=src/"nes_native_video165.h"
    p.write_text(once(p.read_text(),"prefix_sent972;","prefix_sent972,table_sent990;"),newline="\n")
    p=src/"nes_native_sink165.c";s=p.read_text()
    pos=s.index("bool nes_sink212_seal(")
    s=s[:pos]+"""bool nes_table990(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 if(!p->scroll_issued || p->patch_count!=1 || p->patch.size[0]!=21 ||
    p->patch.size[1]!=21 || p->patch.size[2]!=21)return true;
 /* The first literal contains every live HDMA row and its terminator. */
 const uint8_t *table=(const uint8_t*)p+__builtin_offsetof(struct nes_native_video165,patch.mode);
 uint8_t tail[9];
 memcpy(tail,table+240,3);memcpy(tail+3,p->patch.size,6);
 if(!packet(s,2,5,1313,table,240) || !packet(s,2,5,1553,tail,9))return false;
 p->table_sent990=true;
 return true;
}
"""+s[pos:]
    s=once(s,"  uint8_t *joined=",("""  if(!r->map_upload && !nes_table990(s,p))return false;
""" if mode=="late" else "")+"""  if(p->table_sent990){
   if(!packet(s,2,5,offset,raw,192))return false;
  }else{
  uint8_t *joined=""")
    s=once(s,"  offset+=192;","  }\n  offset+=192;")
    # Pin the raw completion to a literal even for a constant source.
    s=once(s,"if(op==2 && n>=4 && !(n&1)){","if(op==2 && n>=4 && !(n&1) && !(section==5 && at==1121 && n==192)){")
    if mode in ("packed","front","gap"):
        s=once(s," uint8_t tail[9];", " static const uint8_t padding[60]={0};")
        a=s.index(" memcpy(tail,table+240");b=s.index(" p->table_sent990=true;",a)
        s=s[:a]+""" if(memcmp(table+183,padding,sizeof padding))return true;
 if(!packet(s,2,5,1313,table,183))return false;
"""+s[b:]
        if mode=="front":
            s=once(s," bool same=same635(s,p);"," if(p->table_sent990 && !packet(s,2,5,1121,raw,192))return false;\n bool same=same635(s,p);")
            s=once(s,"   if(!packet(s,2,5,offset,raw,192))return false;","   /* Both checked ranges have already been submitted. */")
        if mode=="gap":
            s=once(s,"   if(!packet(s,2,5,offset,raw,192))return false;","""   uint8_t ack[12];
   if(!nes_window184_drain(s->plan->window,ack) || !packet(s,2,5,offset,raw,192))return false;""")
    if literal_words:
        # A uniform triplet is still a three-word descriptor. Prevent generic
        # packet RLE from changing it to an opcode with different semantics.
        s=once(s,"section==5 && at==1121 && n==192","section==5 && at==1121 && (n==192 || n==6)")
    if repeat:
        match="packet(s,2,5,offset,raw,192)"
        s=once(s,match,"packet(s,2,5,offset,payload,length)")
        s=once(s,"  if(p->table_sent990){","""  if(p->table_sent990){
   uint8_t words[6];
   const uint8_t *payload=raw;
   unsigned length=192;
   if(!memcmp(raw,raw+2,62) && !memcmp(raw+64,raw+66,62) && !memcmp(raw+128,raw+130,62)){
    for(unsigned i=0;i<3;i++)memcpy(words+i*2,raw+i*64,2);
    payload=words;length=6;
   }""")
    if safe:
        s=once(s," uint8_t descriptor[168];"," if(!r->map_upload && !nes_table990(s,p))return false;\n uint8_t descriptor[168];")
    p.write_text(s,newline="\n")
    if mode=="late":return
    p=src/"nes_native_runtime165.c";s=p.read_text()
    s=once(s,"bool nes_plan_prefix972(void *ctx){","""bool nes_plan_table990(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 extern bool nes_table990(struct nes_native_sink165 *,struct nes_native_video165 *);
 return s->resident->map_upload || nes_table990(&s->sink,s->video);
}
bool nes_plan_prefix972(void *ctx){""")
    p.write_text(s,newline="\n")
    p=src/"nes_planner211.c";s=p.read_text()
    start=s.index("  /* <=7 raw rows");end=s.index("\n }\n p->valid=true;",start)
    table=s[start:end]
    s=s[:start]+s[end:]
    s=once(s,"  memset(&p->patch,0,sizeof(p->patch));","""  memset(&p->patch,0,sizeof(p->patch));
"""+table+"""
  extern bool nes_plan_table990(void *);
  if(!nes_plan_table990(resident->ctx))return fail(p,7);""")
    if safe:
        s=once(s,"  extern bool nes_plan_table990(void *);\n  if(!nes_plan_table990(resident->ctx))return fail(p,7);","")
    p.write_text(s,newline="\n")


def receiver(compact=False,repeat=False):
    labels=read(PACKED/"labels.json")
    body=bytearray((PACKED/"body.bin").read_bytes())
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    def imm(op,value):
        c.emit(op);c.word(value)
    def need(op,fail):
        c.emit(op,3);c.jump(fail)
    def eq(addr,value,fail):
        c.absolute(0xad,addr);imm(0xc9,value);need(0xf0,fail)
    def hook(label,old,where):
        i=labels[label]-ORIGIN
        assert body[i:i+3]==bytes.fromhex(old)
        body[i:i+3]=b'\x4c'+(c.labels[where]&65535).to_bytes(2,"little")
    def resume(label):
        c.absolute(0x4c,(labels[label]+3)&65535)
    for label,old,addr in (("begin","9cd814",0x14d8),("invalidate635","9cd014",0x14d0)):
        where=label+"990"
        c.label(where);c.absolute(0x9c,PENDING);c.absolute(0x9c,addr);resume(label)
        hook(label,old,where)

    c.label("data990")
    c.absolute(0xad,0x1201);imm(0x29,255);imm(0xc9,5);need(0xf0,"normal990")
    c.absolute(0xad,PENDING);c.branch(0xd0,"active990")
    eq(0x1200,0x0502,"normal990");eq(0x108a,1121,"normal990");eq(0x120a,1313,"normal990")
    eq(0x120c,183 if compact else 240,"bad_packet")
    imm(0xa9,1);c.absolute(0x8d,PENDING)
    imm(0xa9,1313);c.absolute(0x8d,0x108a);c.jump("normal990")
    c.label("active990")
    eq(0x1200,0x0502,"bad_packet")
    if not compact:
        c.absolute(0xad,0x108a);imm(0xc9,1553);c.branch(0xd0,"raw990")
        eq(0x120a,1553,"bad_packet");eq(0x120c,9,"bad_packet");c.jump("normal990")
    c.label("raw990")
    eq(0x108a,1562,"bad_packet");eq(0x120a,1121,"bad_packet")
    if repeat:
        c.absolute(0xad,0x120c);imm(0xc9,6);c.branch(0xf0,"valid_raw990")
    eq(0x120c,192,"bad_packet");c.label("valid_raw990")
    imm(0xa9,1121);c.absolute(0x8d,0x108a)
    imm(0xa9,2);c.absolute(0x8d,PENDING)
    c.label("normal990");c.absolute(0xad,0x1201);resume("data")
    hook("data","ad0112","data990")

    c.label("accept990")
    if compact:
        c.absolute(0xad,PENDING);imm(0xc9,1);need(0xf0,"raw_done990")
        eq(0x108a,1496,"done990")
        # Rebuild the omitted suffix in the inactive bank before returning
        # credit. The full semantic validator still runs on canonical WRAM.
        c.absolute(0xae,0x1020)
        base=0x7f6500+1313
        c.emit(0xe2,0x20)
        for off in (20,101,182):
            c.long(0xbf,base+off);need(0xf0,"invalid8")
        c.emit(0xc2,0x20)
        imm(0xa9,0);imm(0xa0,30)
        c.label("zero990");c.long(0x9f,base+183);c.emit(0xe8,0xe8,0x88);c.branch(0xd0,"zero990")
        imm(0xa9,21)
        for i in (0,2,4):c.long(0x9f,base+183+i)
        imm(0xa9,1562);c.absolute(0x8d,0x108a);c.jump("done990")
        c.label("invalid8");c.emit(0xc2,0x20);c.jump("bad_packet")
        c.label("raw_done990")
    c.absolute(0xad,PENDING);imm(0xc9,2);c.branch(0xd0,"done990")
    if repeat:
        c.absolute(0xad,0x108a);imm(0xc9,1127);c.branch(0xd0,"literal_raw990")
        # Expand backwards so every input word is read before its source is overwritten.
        for part in (2,1,0):
            c.absolute(0xae,0x1020);c.long(0xbf,0x7f6500+1121+2*part);imm(0xa0,32)
            label=f"fill990_{part}";c.label(label)
            c.long(0x9f,0x7f6500+1121+64*part);c.emit(0xe8,0xe8,0x88);c.branch(0xd0,label)
        imm(0xa9,1313);c.absolute(0x8d,0x108a)
        c.label("literal_raw990")
    eq(0x108a,1313,"bad_packet")
    imm(0xa9,1562);c.absolute(0x8d,0x108a);c.absolute(0x9c,PENDING)
    c.label("done990");c.absolute(0xad,0x1200);resume("accepted")
    hook("accepted","ad0012","accept990")
    c.label("seal990");c.absolute(0xad,PENDING);need(0xf0,"bad_packet")
    c.absolute(0xad,0x1200);resume("seal")
    hook("seal","ad0012","seal990")
    body.extend(c.finish())
    with patch.object(boot,"STORED",5700):
        boot.build(LOADER_SOURCE,ROOT/"repeat" if repeat else ROOT/"compact" if compact else ROM,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("rom","romcompact","romrepeat","repeatpacked","repeatgap","rlepacked","rlegap","early","late","packed","safefront","safepacked","safegap"));a=p.parse_args()
    if a.mode.startswith("rom"):receiver(a.mode!="rom",a.mode=="romrepeat")
    else:arm(a.mode)
