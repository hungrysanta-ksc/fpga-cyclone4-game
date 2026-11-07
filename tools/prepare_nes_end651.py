"""Independent scheduler changes on the 650 packed ARM. The wire ABI is unchanged."""
import argparse
import shutil
from pathlib import Path
from nes_raw506 import once,sha
from check_nes_fault641 import evidence


def prepare(base,out,mode):
    pin=evidence("geometry650-verification.json")["guards"]["packed"]["firmware"]
    assert sha(base/"src/obj-nes-100/firmware.stm")==pin
    shutil.copytree(base,out,ignore=shutil.ignore_patterns("obj-*",".dep-*","*.log","base-*","*.json"))
    src=out/"src"
    plan=src/"nes_plan_service200.c"
    s=plan.read_text()
    if mode=="handoff":
        # Frame and CRC are already complete. Only drive554 may send the
        # held bank, and its final-mode call cannot yield to ordinary work.
        s=once(s," return drive554(p,p->ending && p->quiet_map);",
                  """ if(p->ending && p->count==1 && p->buffer[4]==0x83)return true;
 return drive554(p,p->ending && p->quiet_map);""")
    elif mode=="grant":
        # In FLUSH, descriptor presence and a writable host plan bank are
        # independent. Submit/validate the tile first, then allow only the
        # already framed END-only E9 to use this positive status sample.
        # FINISH still waits for all bulk receipts. E9 is guarded again.
        s=once(s," if(rx[6]){",""" if(rx[6]){
  uint8_t result=4;
  if(phase==NES_PLAN215_FLUSH && rx[3]==1 && p->ending && p->count==1 &&
     p->buffer[4]==0x83)result|=1;""")
        assert s.count("*flags=4;return true;")==1 and s.count("  *flags=4;\n")==1
        s=s.replace("*flags=4;return true;","*flags=result;return true;").replace("  *flags=4;\n","  *flags=result;\n")
    elif mode=="bg":
        s=once(s," if(!append(p,q))return false;",""" /* Keep room for one more confirmed BG in the second warm bank.
  * If OBJ comes next, publish the seven BGs before buffering that OBJ. */
 if(p->bank_history==2 && p->sent==1 && p->count==7 && p->obj_start==p->bytes && q->kind!=0)
  if(!flush(p))return false;
 if(!append(p,q))return false;""")
        s=once(s,"p->sent==1 && p->count==7 &&\n    (q->kind==0 || (q->kind==1 && p->bytes-p->obj_start==8))",
                 "p->sent==1 && ((p->count==8 && q->kind==0) ||\n    (p->count==7 && q->kind==1 && p->bytes-p->obj_start==8))")
    elif mode=="short":
        sink=src/"nes_native_sink165.c"
        code=once(sink.read_text()," for(unsigned g=s->map_next&127;g<64;){",
                  """ /* Shorten only a speculative map grant while END alone is held.
  * Leave the other map rows for the same monotonically advancing cursor. */
 unsigned limit=(early && s->plan && s->plan->ending && s->plan->count==1)?1:3;
 for(unsigned g=s->map_next&127;g<64;){""")
        sink.write_text(once(code,"while(g<64&&count<3&&","while(g<64&&count<limit&&"),newline="\n")
    plan.write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path);p.add_argument("out",type=Path)
    p.add_argument("mode",choices=("bg","short","handoff","grant"));a=p.parse_args()
    prepare(a.base,a.out,a.mode)
