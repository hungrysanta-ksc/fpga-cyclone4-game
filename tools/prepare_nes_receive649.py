"""Offer one checked input block during output service on the linked 648 path."""
import argparse
import shutil
from pathlib import Path
from nes_raw506 import once,sha
from check_nes_fault641 import evidence


def prepare(base,out,mode):
    assert sha(base/"src/obj-nes-100/firmware.stm")==evidence("tail648-verification.json")["phases"]["1"]["candidate"]["measured"]["firmware_SHA256"]
    shutil.copytree(base,out,ignore=shutil.ignore_patterns("obj-*",".dep-*","*.log"))
    f=out/"src/nes_native_runtime165.c"
    s=f.read_text()
    # Both opportunities belong to immutable current video, after FINISH, and
    # reuse the single seven-poll budget. D3 is exclusively in runtime_step.
    if mode=="credit":
        s=once(s," if(reason==3){",""" if(reason==0 && s->plan.finished &&
    (uint16_t)(s->transport.sent-s->transport.retired)>=2){
  reason=3;progress=false;
 }
 if(reason==3){""")
    else:
        f2=out/"src/nes_native_sink165.c"
        code=once(f2.read_text(),"  s->sequence++;s->state=old;return true;","""  s->sequence++;s->state=old;
  if(section==5 && s->plan && s->plan->finished && s->plan->window &&
     (uint16_t)(s->plan->window->sent-s->plan->window->retired)>=2 &&
     s->plan->window->wait &&
     !s->plan->window->wait(s->plan->ctx,s->plan->guard,4,false))return fail(s,5);
  return true;""")
        f2.write_text(code,newline="\n")
        s=once(s," if(reason==3){",""" bool offered=reason==4;
 if(offered||reason==3){""")
        s=once(s," return nes_cost474_pause(ctx,check,reason,progress);",
            " return nes_cost474_pause(ctx,check,reason,progress||offered);")
        if mode=="sealed":
            s=once(s," bool offered=reason==4;"," bool offered=reason==4;\n if(offered && !s->prefetch_left)return check(ctx);")
            plan=out/"src/nes_plan_service200.c"
            plan.write_text(once(plan.read_text(),"p->bulk_until=p->window->sent;","""p->bulk_until=p->window->sent;
   /* A CRC-checked sealed END with a new descriptor is an input opportunity.
    * The old immutable slot still belongs to bulk_until, through consumption. */
   if(phase==NES_PLAN215_FINISH && rx[3]==2 && p->window->wait &&
      !p->window->wait(p->ctx,p->guard,3,false))return fail(p,2);"""),newline="\n")
    f.write_text(s,newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path);p.add_argument("out",type=Path);p.add_argument("mode",choices=("credit","stream","sealed"))
    a=p.parse_args();prepare(a.base,a.out,a.mode)
