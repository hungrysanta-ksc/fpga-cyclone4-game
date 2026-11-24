"""Profile the 976 slot client's executed planner PCs and hoist immutable row geometry."""
import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from nes_bg976 import WORK as BASE
from nes_plan975 import simulate
from nes_raw506 import once
from replay_nes_supply905 import joint, UC_HOOK_CODE

WORK = BASE.with_name("nes-cell977")
WORD = BASE.with_name("nes-cell977-word")
BUCKET = BASE.with_name("nes-cell977-bucket")
MID = BASE.with_name("nes-cell977-mid")


def instructions():
    listing=(BASE/"link/src/obj-nes-100/nes_planner211.lst").read_text(errors="replace")
    listing=listing.split(".section\t.text.nes_native_video211_plan,",1)[1]
    pcs={}
    line=0
    for row in listing.splitlines():
        if ".size\tnes_native_video211_plan," in row:break
        loc=re.search(r"\.loc 1 (\d+) ",row)
        if loc:line=int(loc[1])
        ins=re.match(r"\s*\d+ ([0-9a-f]{4}) [0-9A-F]+\s+(\S+)(?:\s+(.*))?",row)
        if ins:pcs[int(ins[1],16)]=(line,ins[2],(ins[3] or "").strip().split('@')[0].strip())
    assert pcs[0x49a][:2]==(203,"movs")
    return pcs


def profile(temp,phase):
    original=joint.Runtime.__init__
    pcs=instructions()
    ticks=Counter()
    counts=Counter()
    state={}
    def install(cpu,*args):
        original(cpu,*args)
        base=cpu.syms["nes_native_video211_plan"]
        def begin(u,pc,size,ctx):
            if cpu.generation==911 and not state:
                state.update(start=cpu.clock,last=cpu.clock,key="zero_return")
        def step(u,pc,size,ctx):
            if not state or "end" in state:return
            at=pc-base
            ticks[state["key"]]+=cpu.clock-state["last"]
            state["last"]=cpu.clock
            if at==0x49a:
                state["end"]=cpu.clock
                return
            line,op,arg=pcs[at]
            key=("call:"+arg) if op in ("bl","blx") else str(line)
            state["key"]=key
            counts[key]+=1
        at=cpu.syms["resident_plan213"]
        cpu.u.hook_add(UC_HOOK_CODE,begin,begin=at,end=at)
        cpu.u.hook_add(UC_HOOK_CODE,step,begin=base,end=base+max(pcs))
    with patch.object(joint.Runtime,"__init__",install):
        simulate(temp,phase,"cold",True,BASE,True,tag="977profile",edition=966)
    assert abs(sum(ticks.values())-(state["end"]-state["start"]))<1
    (temp/f"nes-cell977-profile-p{phase}.json").write_text(json.dumps(dict(state=state,ticks=ticks,counts=counts)))


def prepare(word,bucket,mid):
    work=MID if mid else BUCKET if bucket else WORD if word else WORK
    shutil.copytree(BASE/"link",work/"link")
    path=work/"link/src/nes_planner211.c"
    s=path.read_text()
    s=once(s,"  unsigned previous_slot=0,older_slot=0;", """  const uint16_t *cells=s->maps+(s->rows[first[g]]>>3)*33;
  unsigned start=column225(s->raster[first[g]]),split=32-(start&31);
  unsigned page=g*64+(start/32)*2048,at=page+(start&31)*2;
  unsigned previous_slot=0,older_slot=0;""")
    s=once(s,"""  for(unsigned x=0;x<33;x++){
  unsigned idx=(s->rows[first[g]]>>3)*33+x,cell=s->maps[idx];if(cell>>15)return fail(p,6);
  unsigned column=(column225(s->raster[first[g]])+x)&63u;
  unsigned at=((column/32)*1024+g*32+column%32)*2;""", """  for(unsigned x=0;x<33;x++,at+=2){
  if(x==split)at=page^2048;
  unsigned cell=cells[x];if(cell>>15)return fail(p,6);""")
    s=once(s,"cell^s->maps[idx-2]","cell^cells[x-2]")
    if word or bucket or mid:
        s=once(s,""" if(p->map[at]!=(uint8_t)word||p->map[at+1]!=(uint8_t)(word>>8))p->map_dirty|=UINT64_C(1)<<(at/64);
 p->map[at]=(uint8_t)word;p->map[at+1]=(uint8_t)(word>>8);""",""" uint16_t old,value=(uint16_t)word;
 memcpy(&old,p->map+at,sizeof old);
 if(old!=value){
  memcpy(p->map+at,&value,sizeof value);
  p->map_dirty|=UINT64_C(1)<<(at/64);
 }""")
        s=once(s,"unsigned word=(unsigned)p->map[old_at]|((unsigned)p->map[old_at+1]<<8);",
                 "uint16_t word;memcpy(&word,p->map+old_at,sizeof word);")
        s=once(s,"unsigned hint=(p->map[at]|((unsigned)p->map[at+1]<<8))&1023;",
                 "uint16_t stored;memcpy(&stored,p->map+at,sizeof stored);unsigned hint=stored&1023;")
    if bucket or mid:
        s=once(s,"uint32_t reusable474=0;","uint32_t matching_rows[8]={0};")
        s=once(s,"""  if(!exceptional&&(g<4||reused474))for(unsigned h=0;h<g;h++){
   if((reusable474&(UINT32_C(1)<<h))&&
      !memcmp(&s->maps[(s->rows[first[g]]>>3)*33],&s->maps[(s->rows[first[h]]>>3)*33],66)){reuse=h;break;}
  }""","""  const uint16_t *cells=s->maps+(s->rows[first[g]]>>3)*33;
  unsigned bucket=(cells[0]^cells[16]^cells[32])&7;
  if(!exceptional&&(g<4||reused474)){
   uint32_t possible=matching_rows[bucket];
   while(possible){
    unsigned h=__builtin_ctz(possible);
    if(!memcmp(cells,s->maps+(s->rows[first[h]]>>3)*33,66)){reuse=h;break;}
    possible&=possible-1;
   }
  }""")
        s=once(s,"   reusable474|=UINT32_C(1)<<g;reused474++;","   reused474++;")
        s=once(s,"  if(!exceptional)reusable474|=UINT32_C(1)<<g;\n  const uint16_t *cells=s->maps+(s->rows[first[g]]>>3)*33;",
               "  if(!exceptional)matching_rows[bucket]|=UINT32_C(1)<<g;")
        if mid:
            s=once(s,"(cells[0]^cells[16]^cells[32])&7","cells[16]&7")
    path.write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("profile","prepare","run"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    variants=p.add_mutually_exclusive_group()
    variants.add_argument("--word",action="store_true")
    variants.add_argument("--bucket",action="store_true")
    variants.add_argument("--mid",action="store_true")
    a=p.parse_args()
    if a.action=="profile":profile(a.temp,a.phase)
    elif a.action=="prepare":prepare(a.word,a.bucket,a.mid)
    else:simulate(a.temp,a.phase,"cold",True,MID if a.mid else BUCKET if a.bucket else WORD if a.word else WORK,True,
                  tag="977mid" if a.mid else "977bucket" if a.bucket else "977word" if a.word else "977row",edition=966)
