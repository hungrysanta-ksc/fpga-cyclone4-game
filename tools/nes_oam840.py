"""Timestamp finalized OAM, validated queue credit and consumer acceptance."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from check_nes_game478 import UC_HOOK_CODE
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from nes_pair839 import BASE, CLIENT, PROBES, REFERENCE, fixed_pair, oracle, once, sha, stop_pair
from replay_nes_charge836 import trace
from replay_nes_repeat833 import replay
from replay_nes_window837 import MirrorLink, main, reject

OUT = PROBES/"nes-oam840"
MODES = ("beforemap","objend","release")


def link(mode):
    return BASE if mode in ("control","pair") else BASE.parent/("link-840"+mode)


def sender(mode):
    src=BASE/"src"
    dest=OUT/mode
    dest.mkdir(parents=True,exist_ok=True)
    files={}
    def source(name):
        return (src/name).read_text()
    sink="nes_native_sink165.c"
    gate="!p->map_dirty && !p->scroll_issued && p->patch_count==2 && p->objects>28"
    late_oam=" if(!oam227(s,p->oam))return false;"
    text=source(sink)
    if mode=="beforemap":
        # All planner writes and resident preparation have completed. Reuse the
        # normal checked serializer. Ordinary data needs no tile residency.
        text=once(text," if(!map527(s,p,r->map_upload,false))return false;",
                  f" bool early_oam={gate} && !same635(s,p);\n if(early_oam && !oam227(s,p->oam))return false;\n if(!map527(s,p,r->map_upload,false))return false;")
        text=once(text,late_oam,late_oam.replace("if(!oam","if(!early_oam && !oam"))
    else:
        # A completed OBJ planner has fixed all slot and high attribute bytes.
        # Start END before calling ordinary progress. Neither an early packet
        # nor credit commits a bank; all failures take the existing STOP path.
        header="nes_native_sink165.h"
        files[header]=once(source(header),"bool map_pair683;","bool map_pair683, oam_issued840;")
        files[header]=once(files[header],"bool nes_scroll810(", "bool nes_oam840(struct nes_native_sink165 *,const uint8_t *);\nbool nes_scroll810(")
        text=once(text,"static bool oam227(","bool nes_oam840(").replace("oam227(s,p->oam)","nes_oam840(s,p->oam)")
        text=once(text,"s->map_pair683=false;s->sequence=0;","s->map_pair683=false;s->oam_issued840=false;s->sequence=0;")
        text=once(text," if(same&&s->displayed", " if(!s->oam_issued840&&same&&s->displayed")
        text=once(text," if(!nes_oam840(s,p->oam))", " if(!s->oam_issued840 && !nes_oam840(s,p->oam))")
        planner="nes_planner211.c"
        files[planner]=once(source(planner),"if(p->scroll_issued && resident->finish_obj",
                            f"if((p->scroll_issued || ({gate})) && resident->finish_obj")
        runtime="nes_native_runtime165.c"
        files[runtime]=once(source(runtime)," return p->sent || !p->count || p->count>=14 || p->bytes>208 || nes_plan200_end(p);",
                """ if(!s->video->scroll_issued){
  if(!nes_plan200_end(p) || !nes_oam840(&s->sink,s->video->oam))return false;
  s->sink.oam_issued840=true;
  return true;
 }
 return p->sent || !p->count || p->count>=14 || p->bytes>208 || nes_plan200_end(p);""")
        if mode=="release":
            # Once the last map credit is returned, allow section 5 to use
            # the queue instead of polling for the advisory DMA event.
            text=once(text," if(!p->scroll_issued && !p->map_dirty && s->plan && s->plan->window",
                      " if(!s->oam_issued840 && !p->scroll_issued && !p->map_dirty && s->plan && s->plan->window")
    files[sink]=text
    for name,data in files.items():
        (dest/name).write_text(data,newline="\n")


def watch(cpu):
    region=cpu.video+cpu.layout["nes_native_video165"]["oam"]
    counter=cpu.rt+cpu.layout["nes_native_runtime165"]["transport"]+cpu.layout["nes_sink_window184"]["sent"]
    assert cpu.layout["nes_sink_window184"]["retired"]==cpu.layout["nes_sink_window184"]["sent"]+2
    writes=[]
    log=cpu.a.out/"oam840.jsonl"
    def stamp(kind,**kwargs):
        if cpu.generation!=910:return
        a=cpu.u.mem_read(counter,4)
        data=dict(event=kind,clock=cpu.clock,sent=int.from_bytes(a[:2],"little"),
                  retired=int.from_bytes(a[2:],"little"),**kwargs)
        with log.open("a") as f:
            print(json.dumps(data),file=f)
    def written(u,access,at,size,value,user):
        if cpu.generation==910:writes.append(cpu.clock)
    def credit(u,access,at,size,value,user):
        if cpu.generation==910 and value!=int.from_bytes(u.mem_read(at,size),"little"):
            stamp("credit",new_retired=value)
    def wire(u,addr,size,user):
        if cpu.generation!=910:return
        op,section,offset=(u.reg_read(i) for i in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
        if (section==4 and offset==0) or op==3:
            stamp("wire",op=op,section=section,offset=offset,last_store=writes[-1],stores=len(writes))
    cpu.u.hook_add(UC_HOOK_MEM_WRITE,written,begin=region,end=region+543)
    cpu.u.hook_add(UC_HOOK_MEM_WRITE,credit,begin=counter+2,end=counter+3)
    def mark(u,at,size,name):
        if cpu.generation==910:stamp(name,last_store=writes[-1] if writes else None)
    for name in ("nes_sink212_seal","nes_plan200_end"):
        pc=cpu.syms[name]
        cpu.u.hook_add(UC_HOOK_CODE,mark,name,begin=pc,end=pc)
    pc=cpu.syms["packet_wire"]
    cpu.u.hook_add(UC_HOOK_CODE,wire,begin=pc,end=pc)


def run(a):
    arm=link(a.mode)
    temp=Path.home()/"AppData/Local/Temp"
    budget=Path.home()/"Downloads/nes-budget-mmc826.txt"
    client=REFERENCE if a.mode=="control" else CLIENT
    tag="840"+a.mode
    if a.fixed_client and a.opening:
        # The diagnostic switch is only used on the demo clip, after its 2576 ACK.
        client=REFERENCE
        tag+="fixed"
    if a.fixed_client and not a.opening:
        # Only the receiver switches after 2576. The selected ARM runs from reset.
        replay("palette",a.phase,temp,budget,tag=tag+"fixed",client=REFERENCE,arm=arm,
               on_attach=watch,extra_trace=lambda s:trace(CLIENT,False)(fixed_pair(s)))
    elif a.opening:
        with patch.object(sys,"argv",["replay","","","","","",tag,str(budget)]):
            main(PROBES/"nes-tile821/extra01","earlyB","jointmirror",a.phase,temp,
                 arm=arm/"src",link_class=MirrorLink,client=client,client_hash=sha(client/"sink165.sfc"),
                 adapt_template=None if client==REFERENCE else oracle)
    elif a.fault=="pair-stop":
        a.temp,a.budget=temp,budget
        stop_pair(a,arm=arm,tag=tag+"pairstop")
    elif a.fault in ("pulse","coverage"):
        import replay_nes_window837 as test
        original=test.run
        def checked(*args,adapt,**kwargs):
            return original(*args,adapt=lambda s:oracle(adapt(s)),**kwargs)
        a.temp,a.budget,a.arm=temp,budget,"palette"
        with patch.object(test,"run",checked):
            reject(a,client,arm,tag+a.fault)
    else:
        replay("palette",a.phase,temp,budget,tag=tag+(a.fault or ""),client=client,arm=arm,
               fault=a.fault,on_attach=watch,extra_trace=lambda s:trace(client,False)(s if client==REFERENCE else oracle(s)))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("control","pair",*MODES))
    p.add_argument("phase",type=int,nargs="?",choices=(1,2),default=1)
    p.add_argument("--prepare",action="store_true")
    p.add_argument("--opening",action="store_true")
    p.add_argument("--fixed-client",action="store_true")
    p.add_argument("--fault",choices=("pulse","coverage","damage","pair-stop"))
    args=p.parse_args()
    if args.prepare:sender(args.mode)
    else:run(args)
