"""Close an isolated OBJ with the first descriptor from its ready successor run."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from check_nes_plan975 import directory, packet_path, replay
from nes_head980 import baseline, rtl_fixture, simulate
from nes_raw506 import once
from nes_wire964 import fixtures
from test_nes_banks557 import MASTER, host_after
from replay_nes_supply905 import joint, UC_HOOK_CODE, UC_ARM_REG_R2


def work(mode):
    return baseline("returned").with_name("nes-gap981-" + mode)


def prepare(mode):
    src = baseline("returned")/"link"
    dst = work(mode)/"link"
    shutil.copytree(src, dst)
    if mode.startswith("rank"):
        planner = dst/"src/nes_planner211.c"
        s = planner.read_text()
        s = once(s, """ for(unsigned rank=0;rank<8;rank++)for(unsigned i=0;i<s->counts[2];i++){
  uint64_t v=s->objects[i];if(v>>49)return fail(p,8);if(((v>>46)&7)!=rank)continue;""", """ /* BG keys are dead. Link up to 128 fragments into stable NES rank order;
  * no change to slot allocation, per-row evaluation, or OAM priority. */
 uint8_t *next=evaluation+224,*head=next+128;
 memset(head,255,8);
 for(unsigned i=s->counts[2];i--;){
  uint64_t v=s->objects[i];if(v>>49)return fail(p,8);
  unsigned rank=(v>>46)&7;
  next[i]=head[rank];head[rank]=(uint8_t)i;
 }
 for(unsigned rank=0;rank<8;rank++)for(unsigned i=head[rank];i!=255;i=next[i]){
  uint64_t v=s->objects[i];""")
        planner.write_text(s,newline="\n")
        if mode=="rank":
            return
    path = dst/"src/nes_plan_service200.c"
    s = path.read_text()
    # A backward insertion is the first point where this lower slot is
    # known. A hole plus an unbroken run beyond it justifies a second E9.
    at = "  while(at>p->obj_start && p->buffer[4+at-8+3]>q->slot){"
    assert at in s
    trigger = """
 if(encoded[0]==0x81 && at==3 && p->count>=10 && !p->sent &&
    p->bytes==3+8*(p->count-1) && p->window && p->window->last[1]==5){
  uint8_t *b=p->buffer+4;
  unsigned tail=p->count-2;
  if(b[14]>q->slot+1 && b[p->bytes-5]-b[14]+1==tail){
ACTION
  }
 }
"""
    if mode in ("pair","rankpair"):
        action = """   /* BG, isolated OBJ, then a non-adjacent OBJ. The third record
    * closes the 32-byte bank. Keep the remaining adjacent slots buffered. */
   unsigned keep=tail-1;
   uint8_t saved[4];memcpy(saved,b+19,sizeof saved);
   p->bytes=19;p->count=3;
   if(!flush(p))return false;
   memcpy(b+19,saved,sizeof saved);memmove(b,b+19,keep*8);
   p->bytes=keep*8;p->count=keep;
   return true;"""
    elif mode == "ready":
        action = "   return flush(p);"
    else:
        raise ValueError(mode)
    s = once(s, " if(p->count<15 || !p->obj_start)return true;",
             trigger.replace("ACTION",action)+" if(p->count<15 || !p->obj_start)return true;")
    path.write_text(s, newline="\n")
    runtime = dst/"src/nes_native_runtime165.c"
    s = runtime.read_text()
    # Finish before palette production only when all slots have been checked.
    remaining = 1 if mode == "ready" else 11
    s = once(s, "!p->sent && p->count==14",
             f"((!p->sent && p->count==14) || (p->sent==1 && p->count=={remaining}))")
    s = once(s, "return p->sent || !p->count", "return (p->sent && !s->video->prefix_due972) || !p->count")
    runtime.write_text(s, newline="\n")


def run(temp, phase, mode):
    init = joint.Runtime.__init__
    marks = []
    def instrument(cpu,*args):
        init(cpu,*args)
        def issued(u,pc,size,ctx):
            if cpu.generation == 911:
                q = bytes(u.mem_read(u.reg_read(UC_ARM_REG_R2),8))
                marks.append([cpu.clock,int.from_bytes(q[2:4],"little"),q[6],q[7]])
        at = cpu.syms["resident_plan213"]
        cpu.u.hook_add(UC_HOOK_CODE, issued, begin=at, end=at)
    tag = "981"+mode
    with patch.object(joint.Runtime,"__init__",instrument):
        simulate(temp,phase,"cold",True,baseline("returned") if mode=="profile" else work(mode),True,tag=tag,edition=966)
    (directory(temp,phase,tag,"cold")/"slots981.json").write_text(json.dumps(marks))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare","run","rtl","guard"))
    p.add_argument("mode", choices=("profile","pair","ready","rank","rankpair"))
    p.add_argument("temp",type=Path)
    p.add_argument("--phase",type=int,choices=(1,2),default=1)
    p.add_argument("--fault",choices=("bad_seal","stop_decode"))
    a=p.parse_args()
    if a.action=="prepare":
        prepare(a.mode)
    elif a.action=="run":
        run(a.temp,a.phase,a.mode)
    elif a.action=="rtl":
        tag="981"+a.mode
        if a.mode in ("profile","pair"):
            fixtures(a.temp,tag,(a.phase,))
        rtl_fixture(a.temp,a.phase,tag)
        if a.mode in ("profile","pair"):
            root=directory(a.temp,a.phase,tag,"cold")
            d=root/"gen911"
            assert (d/"mail964.txt").read_text().strip()=="none"
            origin=int((d/"origin914.txt").read_text())
            packets=[json.loads(line) for line in (root/"e9wire914-911.jsonl").read_text().splitlines()]
            send=[e for e in json.loads((root/"events.json").read_bytes())
                  if e.get("opcode")=="0xe9" and e["generation"]==911]
            edges=[]
            for i,(e,(end,wire)) in enumerate(zip(send,packets,strict=True)):
                assert e["clock"]==end
                bits=[7.5]+[(4+k)*8+7.5 for k in range(len(bytes.fromhex(wire))-8)]
                ticks=[round(host_after(e["start"]+bit*MASTER/2625000,3))-origin for bit in bits]
                edges.append(" ".join(map(str,[i,*ticks])))
            (d/"admission954.txt").write_text("\n".join(edges)+"\n")
    else:
        tag="981"+a.mode
        trace=directory(a.temp,a.phase,tag,"cold")
        commands,_=packet_path(trace,911)
        replay(a.temp,trace,a.temp/f"nes-{tag}-{a.fault}","control",commands,911,a.fault)
