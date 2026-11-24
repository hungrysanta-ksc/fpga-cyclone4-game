"""Give accepted tiles an idle DMA opportunity while the literal tail is on SPI."""
import argparse
import json
import math
import shutil
from pathlib import Path

from check_nes_plan975 import directory, packet_path, read, replay
from nes_cell977 import simulate
from nes_cutoff982 import observer
from nes_head980 import baseline
from nes_raw506 import once


def work(where):
    return baseline("returned").with_name("nes-tile985-"+where)


def prepare(where):
    dst=work(where)/"link"
    shutil.copytree(baseline("returned")/"link",dst)
    src=dst/"src/nes_native_sink165.c"
    anchor=("  if(!packet(s,2,5,offset,joined,201))return false;" if where=="between" else
            "  if(!packet(s,2,5,offset+201,joined+201,240))return false;")
    src.write_text(once(src.read_text(),anchor,anchor+"""
  /* Open an idle-consumer window only after the queue confirms retirement.
   * The 65816 still checks STOP and all newly arrived heads before tile DMA. */
  if(!r->map_upload && p->patch_count==1 && s->plan && s->plan->window){
   uint8_t receipt[12];
   if(!nes_window184_drain(s->plan->window,receipt))return fail(s,5);
  }"""),newline="\n")


def isolated(temp,phase,where):
    src=directory(temp,phase,"978returned","cold")
    commands,ledger=packet_path(src,911)
    head=ledger[-2 if where=="between" else -1]
    previous=ledger[-3 if where=="between" else -2]
    assert previous["section"]==5 and previous["op"]==2
    assert head["op"]==(2 if where=="between" else 3)
    e1=0
    free=0
    shifts=[]
    for e in read(src/"events.json"):
        if e.get("event")!="SPI":continue
        if e["opcode"]=="0xe1":e1+=1
        if e1>len(commands):break
        start=max(free,e["start"])
        if e["opcode"]=="0xe1" and e1==head["index"]:
            # Zero-cost notification is an optimistic causal control. Charge
            # the real transfer duration and serialize every later bus user.
            start=max(start,previous["ack"])
        free=start+(e["clock"]-e["start"])
        if free-e["clock"]>0.01:
            shifts.append([e["opcode"],start,free])
            if e["opcode"]=="0xe1":
                c=commands[e1-1]
                assert abs(c[2]-e["clock"])<1
                commands[e1-1]=(*c[:2],math.ceil(free),*c[3:])
    out=temp/f"nes-tile985-fixed-{where}-p{phase}"
    replay(temp,src,out,"fixed",commands,911,observe=observer(src))
    (out/"retimed985.json").write_text(json.dumps(shifts))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run","fixed","guard"))
    p.add_argument("where",choices=("between","after"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--fault",choices=("stop_decode","bad_seal"))
    a=p.parse_args()
    tag="985"+a.where
    if a.action=="prepare":prepare(a.where)
    elif a.action=="fixed":isolated(a.temp,a.phase,a.where)
    elif a.action=="guard":
        if not a.fault:p.error("guard requires --fault")
        src=directory(a.temp,a.phase,tag,"cold")
        cmds,_=packet_path(src,911)
        replay(a.temp,src,a.temp/f"nes-{tag}-p{a.phase}-{a.fault}","fixed",cmds,911,a.fault)
    else:simulate(a.temp,a.phase,"cold",True,work(a.where),True,tag=tag,edition=966)
