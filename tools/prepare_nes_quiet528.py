# SPDX-License-Identifier: MIT
"""Offer one committed map packet per unused END-flush poll, ahead of SEAL."""
import argparse
import json
from pathlib import Path

from nes_raw506 import once, sha


def prepare(src, out):
    evidence = Path(__file__).resolve().parents[1] / 'analysis/map527-verification.json'
    assert sha(src/'obj-nes-100/firmware.stm') == json.loads(evidence.read_text())['builds']['frontier']['sha256']
    out.mkdir(parents=True, exist_ok=False)

    def edit(name, old, new):
        (out/name).write_text(once((src/name).read_text(), old, new), newline='\n')

    edit('nes_plan_service200.h', 'uint8_t buffer[248];',
         'bool (*quiet_map)(void *); /* Only armed around the final plan flush. */\n uint8_t buffer[248];')
    edit('nes_plan_service200.c', '  if(!wait485(p))return false;\n }\n return fail(p,6);\n}\nstatic bool append',
         '''  /* E9 returned above, ready or repeated bulk has flags=4. Preserve a queue slot. */
  if(flags==0 && p->quiet_map && (uint16_t)(p->window->sent-p->window->retired)<3)
   if(!p->quiet_map(p->ctx))return fail(p,5);
  if(!wait485(p))return false;
 }
 return fail(p,6);
}
static bool append''')
    edit('nes_native_sink165.c','static bool map527(', 'bool map527(')
    edit('nes_native_sink165.h','bool nes_sink527_early(',
         'bool map527(struct nes_native_sink165 *,struct nes_native_video165 *,uint64_t,bool);\nbool nes_sink527_early(')
    name='nes_native_runtime165.c'
    s=once((src/name).read_text(),'static bool planner221(','''static bool quiet528(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 unsigned before=s->sink.map_next;
 if(!map527(&s->sink,s->video,s->resident->map_upload,true))return false;
 if(s->sink.map_next==before || s->sink.map_next==64)s->plan.quiet_map=NULL;
 return true;
}
static bool planner221(''')
    s=once(s,'  if(!nes_plan200_end(&s->plan))return fail(s,NES_RUNTIME165_DISPLAY);','''  s->plan.quiet_map=quiet528;
  bool end_ok=nes_plan200_end(&s->plan);
  s->plan.quiet_map=NULL;
  if(!end_ok)return fail(s,NES_RUNTIME165_DISPLAY);''')
    (out/name).write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    prepare(a.arm,a.out)
