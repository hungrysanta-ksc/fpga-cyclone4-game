"""Build alternative credit scheduling policies from the checked 652/653 MCU."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once

def arm(base,out,mode):
    assert digest(base/"src/obj-nes-100/firmware.stm")==evidence("direct653-verification.json")["firmware"]
    shutil.copytree(base,out,ignore=shutil.ignore_patterns("obj-*",".dep-*","*.log","base-*","*.json"))
    p=out/"src/nes_plan_service200.c";s=p.read_text()
    if mode in ("service","combined"):
        # On an empty grant use the normal output owner for a single command.
        # Positive E8 credit still wins; SEAL and HDMA cannot yield this way.
        s=once(s," return drive554(p,p->ending && p->quiet_map);",""" if(p->ending && p->count==1 && p->buffer[4]==0x83 && p->quiet_map)return true;
 return drive554(p,p->ending && p->quiet_map);""")
        s=once(s,"if(mode==NES_MAP553 && p->bulk_pending &&","if((mode==NES_MAP553 || mode==NES_ORDINARY553) && p->bulk_pending &&")
    if mode in ("batch","combined"):
        s=once(s," if(!append(p,q))return false;",""" if(p->bank_history==2 && p->sent==1 && p->count==7 && p->obj_start==p->bytes && q->kind!=0)
  if(!flush(p))return false;
 if(!append(p,q))return false;""")
        s=once(s,"p->sent==1 && p->count==7 &&\n    (q->kind==0 || (q->kind==1 && p->bytes-p->obj_start==8))",
                 "p->sent==1 && ((p->count==8 && q->kind==0) ||\n    (p->count==7 && q->kind==1 && p->bytes-p->obj_start==8))")
    if mode=="front":
        runtime=out/"src/nes_native_runtime165.c"
        code=once(runtime.read_text()," return nes_sink527_early(&s->sink,s->video,s->resident);",""" /* Two confirmed plan banks can feed ROM while the later map cursor progresses.
  * A skipped speculative offer leaves its range pending for map527/seal. */
 if(s->plan.bank_history==2 && s->plan.sent<2)return true;
 return nes_sink527_early(&s->sink,s->video,s->resident);""")
        runtime.write_text(code,newline="\n")
    p.write_text(s,newline="\n")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path);p.add_argument("out",type=Path);p.add_argument("mode",choices=("service","batch","combined","front"))
    a=p.parse_args();arm(a.base,a.out,a.mode)
