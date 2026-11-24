"""Publish the immutable OAM literal before its fill, then open a verified idle DMA window."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import nes_page963
from boot_nes_column854 import build
from build_nes_trace_replay import Code
from check_nes_plan975 import directory, packet_path, replay
from nes_blank959 import LOADER_SOURCE, ORIGIN
from nes_blank960 import PACKED
from nes_cell977 import simulate
from nes_head980 import baseline
from nes_raw506 import once
from nes_tile985 import work as idle

MODES=("prefix","between","after","literal")
FAST={"fastbase":baseline("returned"),"fastidle":idle("after")}
ROM=baseline("returned").with_name("nes-oam988-rom")


def work(mode):
    return baseline("returned").with_name("nes-oam988-"+mode)


def prepare(mode):
    dst=work(mode)/"link"
    source=idle("after") if mode=="literal" else baseline("returned")
    shutil.copytree(source/"link",dst)
    src=dst/"src"
    if mode=="literal":
        path=src/"nes_native_sink165.c"
        code=once(path.read_text(),"if(op==2 && n>=4 && !(n&1)){",
                  "if(op==2 && n>=4 && !(n&1) && !(section==4 && at==512 && n==32)){")
        path.write_text(code,newline="\n")
        return
    header=src/"nes_native_sink165.h"
    header.write_text(once(header.read_text(),"uint8_t disable_column;","uint8_t disable_column,oam_prefix988;"),newline="\n")
    path=src/"nes_native_sink165.c"
    code=path.read_text()
    code=once(code,"s->strip_dma_seen=false;s->sequence=0","s->oam_prefix988=0;s->strip_dma_seen=false;s->sequence=0")
    scan=""" unsigned first=508;
 while(first>=4&&!memcmp(b+first-4,b+508,4))first-=4;"""
    helper="static unsigned oam_first988(const uint8_t *b){\n"+scan+"\n return first;\n}\n"
    code=once(code,scan," unsigned first=s->oam_prefix988?s->oam_prefix988:oam_first988(b);")
    code=once(code,"static bool oam227(",helper+"static bool oam227(")
    code=once(code," if(first&&!span(s,4,0,b,first))"," if(first&&!s->oam_prefix988&&!span(s,4,0,b,first))")
    code=once(code," p->prefix_sent972=true;",""" unsigned first=oam_first988(p->oam);
 if(first && first<=240 && memcmp(p->oam+508,p->oam+510,2)){
  /* Only the finalized leading OAM bytes move here. The repeat and
   * high attributes retain their original coverage and service order. */
  if(!packet(s,24,4,0,p->oam,first))return false;
  s->oam_prefix988=(uint8_t)first;
 }
 p->prefix_sent972=true;""")
    if mode!="prefix":
        anchor=("  if(!packet(s,2,5,offset,joined,201))return false;" if mode=="between" else
                "  if(!packet(s,2,5,offset+201,joined+201,240))return false;")
        code=once(code,anchor,anchor+"""
  if(s->oam_prefix988 && !r->map_upload && s->plan && s->plan->window){
   uint8_t receipt[12];
   if(!nes_window184_drain(s->plan->window,receipt))return fail(s,5);
  }""")
    path.write_text(code,newline="\n")


def receiver():
    labels=json.loads((PACKED/"labels.json").read_bytes())
    body=bytearray((PACKED/"body.bin").read_bytes())
    def patch_bytes(address,old,new):
        i=address-ORIGIN
        assert len(old)==len(new) and body[i:i+len(old)]==old
        body[i:i+len(old)]=new
    hole=ORIGIN+body.index(b'\xea'*42,labels["compare635"]-ORIGIN,labels["save635"]-ORIGIN)
    c=Code(hole)
    c.labels.update(labels)
    c.emit(0xc9,5);c.branch(0xd0,"oam988");c.jump("uniform608")
    c.label("oam988");c.emit(0xc9,4);c.branch(0xd0,"word988")
    c.long(0xaf,0x400010);c.long(0xcf,0x400011);c.branch(0xd0,"word988")
    c.emit(0xc2,0x20);c.absolute(0xad,0x120c);c.emit(0xc9,32,0);c.branch(0xd0,"old16")
    c.absolute(0xae,0x120a);c.emit(0xe0,0,2);c.branch(0xd0,"old16")
    c.labels["fixed988"]=labels["generic548"]+10
    c.jump("fixed988");c.label("old16");c.jump("word16_516")
    c.label("word988");c.jump("word516")
    fast=c.finish()
    patch_bytes(hole,b'\xea'*len(fast),fast)
    patch_bytes(labels["repeated1815"]+7,bytes.fromhex("c905d065"),b'\x4c'+(hole&65535).to_bytes(2,"little")+b'\xea')
    patch_bytes(labels["zero_chunk516"]+18,bytes.fromhex("c90300d003"),bytes.fromhex("c90500f003"))
    assert body[labels["generic548"]+10-ORIGIN:labels["generic548"]+12-ORIGIN]==b'\x85\x60'
    # Record physical capacity separately if this packed program overflows.
    import boot_nes_column854 as boot
    with patch.object(boot,"STORED",5200):
        build(LOADER_SOURCE,ROM,bytes(body),labels,compact_mvn=True,minimum=2,short_pairs=True)


def observe_launch(original):
    def launch(args,*rest,**kwargs):
        if "--testRunner" not in args:return original(args,*rest,**kwargs)
        path=Path(args[args.index("--testRunner")+1])
        source=once(path.read_text(encoding="utf-8"),"local function uniform545()", """local function uniform545()
 if packet and pb(0)==4 and pb(1)==4 and pw(10)==512 and pw(12)==2 and pw(14)==32 then
  return pb(16)==pb(17)
 end""")
        source=once(source,"   for j=0,fillBytes545-1", """   if pb(1)==4 then address=0x10000+word(0x1020)+0x6200+pw(10) end
   for j=0,fillBytes545-1""")
        path.write_text(source,encoding="utf-8",newline="\n")
        return original(args,*rest,**kwargs)
    return launch


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","rom","run","guard"));p.add_argument("mode",choices=(*MODES,*FAST));p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1);p.add_argument("--fault",choices=("bad_seal","stop_decode"))
    a=p.parse_args()
    tag="988"+a.mode+("wram" if a.mode in FAST else "")
    if a.action=="rom":receiver()
    elif a.action=="prepare":prepare(a.mode)
    elif a.action=="run" and a.mode in FAST:
        with patch.object(nes_page963,"PACKED",ROM),patch.object(subprocess,"Popen",observe_launch(subprocess.Popen)):
            simulate(a.temp,a.phase,"cold",True,FAST[a.mode],True,tag=tag,edition=966)
    elif a.action=="run":simulate(a.temp,a.phase,"cold",True,work(a.mode),True,tag=tag,edition=966)
    else:
        if not a.fault:p.error("guard needs --fault")
        d=directory(a.temp,a.phase,tag,"cold")
        cmds,_=packet_path(d,911)
        replay(a.temp,d,a.temp/f"nes-{tag}-p{a.phase}-{a.fault}","fixed",cmds,911,a.fault)
