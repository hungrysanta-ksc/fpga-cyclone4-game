"""Isolate final E0 polling and move the checked OAM queue drain before bulk service."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch

from unicorn.arm_const import UC_ARM_REG_R2, UC_ARM_REG_SP
from nes_cell977 import MID, simulate
from nes_raw506 import once
from replay_nes_supply905 import joint, UC_HOOK_CODE


def work(mode):
    return MID.with_name("nes-capture978-"+mode)


def prepare(mode):
    dest=work(mode)/"link"
    shutil.copytree(MID/"link",dest)
    path=dest/"src/nes_native_sink165.c"
    s=path.read_text()
    start=s.index(" /* Let an already submitted OBJ return")
    end=s.index(" /* The original span",start)
    old=s[start:end]
    if mode=="returned":
        # Keep both bulk checks: the first may submit a 32B OBJ, the
        # second may publish its successor. Extend only the gap between them.
        path.write_text(once(s,"last[1]==4?1:12","last[1]==4?1:24"),newline="\n")
        return
    if mode in ("idle","grant","bank"):
        # Give the already accepted OBJ run an idle window before the next
        # 64B bank descriptor occupies the head. Every E0 still checks credit.
        gate=""" if(op==23 && section && expanded==64 && s->plan->window->last[1]==1){
  uint8_t receipt[12];
  for(unsigned i=0;i<12;i++)
   if(!nes_window184_drain(s->plan->window,receipt))return fail(s,5);
 }
"""
        # Both cases run the regular bulk progress operation once below.
        old=old.replace(" && nes_plan200_progress(s->plan,NES_ORDINARY553)","")
        s=s[:start]+s[end:]
        if mode in ("grant","bank"):
            gate=""" if(op==23 && section && expanded==64 && s->plan->window->last[1]==1 &&
    !wait_map880(s->plan->window,24))return fail(s,5);
"""
            s=once(s,"uint8_t ack[12];\n do {","uint8_t ack[12];\n bool hold=limit==24;\n do {")
            s=once(s,"if(w->status_flags&8)break;","if((!hold || limit<=12) && (w->status_flags&8))break;")
            if mode=="bank":
                old=""
        anchor=" if(s->plan && op>=2 && op!=7"
        path.write_text(once(s,anchor,gate+old+anchor),newline="\n")
        return
    s=s[:start]+s[end:]
    anchor=" if(s->plan && op>=2 && op!=7"
    # Drain with the previous head still selected. A subsequently ready OBJ
    # can then claim the bank without competing against this OAM packet.
    gate=old.replace(" && nes_plan200_progress(s->plan,NES_ORDINARY553)","")
    if mode=="hold":
        gate=gate.replace("s->plan->window->last[1]==4?1:12","s->plan->window->last[1]==4?1:24")
        s=once(s,"if(w->status_flags&8)break;","if(limit<=12 && (w->status_flags&8))break;")
        # Existing long map waits retain their early exit.
        s=once(s,"uint8_t ack[12];\n do {","uint8_t ack[12];\n bool hold=limit==24;\n do {")
        s=once(s,"if(limit<=12 && (w->status_flags&8))","if((!hold || limit<=12) && (w->status_flags&8))")
    path.write_text(once(s,anchor,gate+anchor),newline="\n")


def run(temp,phase,mode):
    original=joint.Runtime.__init__
    def instrument(cpu,*args):
        original(cpu,*args)
        if mode!="paced":return
        pc=cpu.syms["nes_cost474_pause"]
        def enter(u,at,size,ctx):
            if cpu.generation==909 and u.reg_read(UC_ARM_REG_R2)==2:
                sp=u.reg_read(UC_ARM_REG_SP)
                if int.from_bytes(u.mem_read(sp,4),"little")==0:
                    u.mem_write(sp,(84*160).to_bytes(4,"little"))
        cpu.u.hook_add(UC_HOOK_CODE,enter,begin=pc,end=pc)
    with patch.object(joint.Runtime,"__init__",instrument):
        simulate(temp,phase,"cold",True,MID if mode=="paced" else work(mode),True,tag="978"+mode,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","run"))
    p.add_argument("mode",choices=("paced","early","hold","idle","grant","bank","returned"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    a=p.parse_args()
    if a.action=="prepare":prepare(a.mode)
    else:run(a.temp,a.phase,a.mode)
