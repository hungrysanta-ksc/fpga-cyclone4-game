"""Attribute the linked ARM's 911 BG interval to measured call/return pairs."""
import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from nes_plan975 import BASE, simulate
from nes_raw506 import once
from replay_nes_supply905 import joint, UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_R3

WORK = BASE.with_name("nes-bg976")
ROWS = BASE.with_name("nes-bg976-rows")
EQUAL = BASE.with_name("nes-bg976-equal")


def prepare(rows,equal):
    work=EQUAL if equal else ROWS if rows else WORK
    shutil.copytree(BASE/"link", work/"link")
    path=work/"link/src/nes_planner211.c"
    body=path.read_text()
    if equal:
        body=once(body,"   for(unsigned x=0;x<33;x++){\n    unsigned c=(old_column", """   if(old_column==new_column && bank[g]==bank[reuse]){
    unsigned left=33,c=new_column;
    while(left){
     unsigned n=32-(c&31);if(n>left)n=left;
     const uint8_t *page=p->map+(c/32)*2048+(c&31)*2;
     if(memcmp(page+g*64,page+reuse*64,n*2))break;
     left-=n;c=(c+n)&63;
    }
    if(!left)goto equal_row976;
   }
   for(unsigned x=0;x<33;x++){
    unsigned c=(old_column""")
        body=once(body,"   reusable474|=UINT32_C(1)<<g;reused474++;","equal_row976:\n   reusable474|=UINT32_C(1)<<g;reused474++;")
        path.write_text(body,newline="\n")
        return
    if rows:
        # Both rows already belong to the same immutable committed input.
        # Compare actual destination words and retain untouched offscreen cells.
        body=once(body,"   for(unsigned x=0;x<33;x++){\n    unsigned c=(old_column", """   if(old_column==new_column && bank[g]==bank[reuse]){
    unsigned c=new_column,left=33;
    while(left){
     unsigned n=32-(c&31);if(n>left)n=left;
     unsigned base=(c/32)*2048+(c&31)*2;
     uint8_t *dst=p->map+base+g*64;
     const uint8_t *src=p->map+base+reuse*64;
     if(memcmp(dst,src,n*2)){
      memcpy(dst,src,n*2);
      p->map_dirty|=UINT64_C(1)<<((c/32)*32+g);
     }
     left-=n;c=(c+n)&63;
    }
   }else for(unsigned x=0;x<33;x++){
    unsigned c=(old_column""")
        path.write_text(body,newline="\n")
        return
    position="""  unsigned column=(column225(s->raster[first[g]])+x)&63u;
  unsigned at=((column/32)*1024+g*32+column%32)*2;"""
    body=once(body,position,"")
    body=once(body,"  unsigned slot;\n  if(x>=2",position+"\n  unsigned slot;\n  if(x>=2")
    body=once(body,"  /*484 All40", """  /* The old map word is only a slot hint. The destination must still own
   * that pattern and this planner must already have pinned its exact key. */
  unsigned hint=(p->map[at]|((unsigned)p->map[at+1]<<8))&1023;
  unsigned mask=1u<<(hint&7);
  if(!exceptional && hint &&
     (resident->used[hint>>3]&resident->resident[resident->target][hint>>3]&mask) &&
     p->bg_keys[hint]==((cell&8191)|UINT64_C(0x1fed6c8da4480000))){
   slot=hint;
  }else{
  /*484 All40""")
    body=once(body,"  if(slot>=1024)return fail(p,7);","  if(slot>=1024)return fail(p,7);\n  }")
    path.write_text(body,newline="\n")


def profile(temp,phase):
    original=joint.Runtime.__init__
    marks={}
    elapsed=Counter()
    counts=Counter()
    calls=[]
    pending={}
    lst=(BASE/"link/src/obj-nes-100/nes_planner211.lst").read_text(errors="replace")
    def install(cpu,*args):
        original(cpu,*args)
        base=cpu.syms["nes_native_video211_plan"]
        def hook(at,callback):
            def hit(u,pc,size,ctx):
                if cpu.generation==911:
                    callback(u,cpu.clock)
            cpu.u.hook_add(UC_HOOK_CODE,hit,begin=at,end=at)
        def mark(key):
            return lambda u,t:marks.setdefault(key,t)
        hook(cpu.syms["resident_plan213"],mark("zero"))
        hook(cpu.syms["offer527"],mark("offer"))
        assert re.search(r"04b0\s+0020\s+movs\s+r0, #0",lst)
        hook(base+0x4b0,mark("hdma"))
        for offset,name in re.findall(r"\b([0-9a-f]{4}) FFF7FEFF\s+bl\s+(tile|nes_resident211_slot|map_word185)\s*$",lst,re.M):
            at=int(offset,16)
            def enter(u,t,at=at,name=name):
                if "zero" not in marks or "hdma" in marks:return
                assert at not in pending
                key=(u.reg_read(UC_ARM_REG_R3)<<32)|u.reg_read(UC_ARM_REG_R2)
                pending[at]=(t,key)
            def leave(u,t,at=at,name=name):
                if at not in pending:return
                start,key=pending.pop(at)
                elapsed[name]+=t-start
                counts[name]+=1
                if name=="nes_resident211_slot":
                    calls.append([key,u.reg_read(UC_ARM_REG_R0)])
            hook(base+at,enter)
            hook(base+at+4,leave)
    with patch.object(joint.Runtime,"__init__",install):
        simulate(temp,phase,"cold",True,BASE,True,tag="976profile",edition=966)
    assert not pending and marks["zero"]<marks["hdma"]<marks["offer"]
    (temp/f"nes-bg976-profile-p{phase}.json").write_text(json.dumps(dict(marks=marks,elapsed=elapsed,counts=counts,calls=calls)))


def count_calls(temp,work,tag):
    original=joint.Runtime.__init__
    counts=Counter()
    state={}
    def install(cpu,*args):
        original(cpu,*args)
        for name in ("resident_plan213","nes_resident211_slot","map_word185","offer527"):
            at=cpu.syms[name]
            def hit(u,pc,size,ctx,name=name):
                if cpu.generation!=911:return
                if name=="resident_plan213":
                    state.setdefault("start",cpu.clock)
                elif name=="offer527":
                    state.setdefault("end",cpu.clock)
                elif "start" in state and "end" not in state:
                    counts[name]+=1
            cpu.u.hook_add(UC_HOOK_CODE,hit,begin=at,end=at)
    with patch.object(joint.Runtime,"__init__",install):
        simulate(temp,1,"cold",True,work,True,tag=tag+"count",edition=966)
    (temp/f"nes-{tag}-counts.json").write_text(json.dumps(dict(marks=state,counts=counts)))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("profile","prepare","run","count"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    variant=p.add_mutually_exclusive_group()
    variant.add_argument("--rows",action="store_true")
    variant.add_argument("--equal",action="store_true")
    a=p.parse_args()
    work=EQUAL if a.equal else ROWS if a.rows else WORK
    tag="976equal" if a.equal else "976rows" if a.rows else "976hint"
    if a.action=="count":
        if a.phase!=1:p.error("call counts use phase 1")
        count_calls(a.temp,work,tag)
    elif a.action=="profile":
        profile(a.temp,a.phase)
    elif a.action=="prepare":
        prepare(a.rows,a.equal)
    else:
        simulate(a.temp,a.phase,"cold",True,work,True,tag=tag,edition=966)
