"""Reorder scroll and plan on frames with a zero BG and no dirty map."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_page963 import simulate
from nes_raw506 import once
from nes_token973 import source
from replay_nes_supply905 import joint, UC_HOOK_CODE

BASE = source("before232")
WORK = BASE.with_name("nes-plan975")
KEYS = BASE.with_name("nes-plan975-keys")


def prepare(keys):
    work = KEYS if keys else WORK
    shutil.copytree(BASE/"link", work/"link")
    src = work/"link/src"
    if keys:
        # 755's optimization, isolated on the 973 planner. Resident begin()
        # clears used bits; inserted keys are written before their first lookup.
        planner = src/"nes_planner211.c"
        planner.write_text(once(planner.read_text(), " memset(p,0,offsetof(struct nes_native_video165,map));", ""), newline="\n")
        return
    header = src/"nes_native_video165.h"
    header.write_text(once(header.read_text(), "bool scroll_issued,", "bool defer_scroll975, scroll_issued,"), newline="\n")
    runtime = src/"nes_native_runtime165.c"
    body = once(runtime.read_text(), " return nes_sink527_early(&s->sink,s->video,s->resident,final) &&",
                """ if(!nes_sink527_early(&s->sink,s->video,s->resident,final))return false;
 uint64_t map=s->resident->map_stale[s->resident->target]|s->video->map_dirty;
 if(!map && s->video->patch_count==1 && s->plan.bank_history==2 &&
    !s->plan.sent && s->plan.count==1 && s->plan.bytes==3 && s->plan.buffer[4]==0x82){
  s->video->defer_scroll975=true;
  return true;
 }
 return""")
    body = once(body," return p->sent || !p->count || p->count>14 || p->bytes>208 || nes_plan200_end(p);",
                """ if(!p->sent && p->count && p->count<=14 && p->bytes<=208 && !nes_plan200_end(p))return false;
 return !s->video->defer_scroll975 || nes_scroll810(&s->sink,s->video,0,s->receiver->counts[2]);""")
    runtime.write_text(body,newline="\n")
    planner = src/"nes_planner211.c"
    planner.write_text(once(planner.read_text(), "if(p->scroll_issued && resident->finish_obj",
                            "if((p->scroll_issued || p->defer_scroll975) && resident->finish_obj"), newline="\n")


def profile(temp,phase):
    original=joint.Runtime.__init__
    marks=[]
    def instrument(cpu,*args):
        original(cpu,*args)
        for name in ("nes_native_video211_plan","resident_plan213","offer527","nes_scroll810","finish_obj810"):
            at=cpu.syms[name]
            def hit(u,pc,size,ctx,label=name):
                if cpu.generation==911:
                    marks.append((label,cpu.clock))
            cpu.u.hook_add(UC_HOOK_CODE,hit,begin=at,end=at)
    with patch.object(joint.Runtime,"__init__",instrument):
        simulate(temp,phase,"cold",True,BASE,True,tag="975profile",edition=966)
    (temp/f"nes-plan975-p{phase}.json").write_text(json.dumps(marks))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run","profile"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--keys",action="store_true")
    a=p.parse_args()
    if a.action=="prepare":
        prepare(a.keys)
    elif a.action=="profile":
        profile(a.temp,a.phase)
    else:
        simulate(a.temp,a.phase,"cold",True,KEYS if a.keys else WORK,True,
                 tag="975keys" if a.keys else "975defer",edition=966)
