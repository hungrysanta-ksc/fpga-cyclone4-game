# SPDX-License-Identifier: MIT
"""Reschedule the existing palette, map drain and compact raw preparation."""
import argparse
import shutil
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out, policy):
    assert sha(base/'src/obj-nes-100/firmware.stm') == 'e25814c61a9d70543d2971677b94055577412c9ed9c11a329272ecc61772985f'
    shutil.copytree(base, out, ignore=shutil.ignore_patterns('obj-*', '.dep-*', '*.log'))
    path = out/'src/nes_native_sink165.c'
    code = path.read_text()
    palette = ' if(!span(s,3,0,p->cgram,512))return false;\n'
    # 128 and 384 are whole-word spans. Both go through the existing cost
    # choice, credit guard and checked packet writer for arbitrary CGRAM data.
    lead = ' if(!span(s,3,0,p->cgram,128))return false;\n' if policy=='split' else ''
    code = once(code, palette, lead)
    if policy=='split':
        palette = ' if(!span(s,3,128,p->cgram+128,384))return false;\n'
    if policy == 'shared-order':
        begin = code.index(' /* Allow a long accepted map tail')
        end = code.index(' if((((uint32_t)(r->map_upload>>32))',begin)
        init = '  unsigned packed=2048;const uint8_t *raw=p->patch.chr;'
        # Keep just one copy of each operation. The second phase performs
        # whichever operation the first phase omitted.
        body = once(code[begin:end],init+'\n','')
        stages = init + '''
 bool small_bg=s->obj_next && (unsigned)(s->bg_next-1)<4;
 for(unsigned phase=0;phase<2;phase++){
  if(phase!=(unsigned)small_bg){
   if(!span(s,3,0,p->cgram,512))return false;
   continue;
  }
''' + body + ' }\n'
        path.write_bytes((code[:begin]+stages+code[end:]).encode())
        return
    if policy in ('small-bg','small-shared-cost'):
        # An issued OBJ proves the planner has passed the ordered BG prefix.
        # bg_next counts successfully submitted 16B units, not DMA completion.
        marker = ' /* Allow a long accepted map tail'
        code = once(code, marker, ''' bool small_bg=s->obj_next && (unsigned)(s->bg_next-1)<4;
 if(small_bg && !span(s,3,0,p->cgram,512))return false;
''' + marker)
        palette = ' if(!small_bg && !span(s,3,0,p->cgram,512))return false;\n'
        anchor = ' if((((uint32_t)(r->map_upload>>32))'
    elif policy == 'advance':
        anchor = ' /* Allow a long accepted map tail'
    elif policy in ('after-pack','credit-only'):
        anchor = ' if((((uint32_t)(r->map_upload>>32))'
    else:
        anchor = ' if(!oam227(s,p->oam)'
    code = once(code, anchor, palette + anchor)
    if policy=='credit-only':
        # The long-map drain only creates idle time. Normal admission and the
        # checked final barrier still own every transfer/retirement.
        code = once(code, 'if(s->plan && s->plan->window &&',
                    'if((!s->obj_next || (unsigned)(s->bg_next-1)>=4) && s->plan && s->plan->window &&')
    if policy=='small-shared-cost':
        # span() and the OAM estimator compare exactly the same two encodings.
        # Keep the original strict preference for the legacy format on ties.
        start = code.index(' unsigned oldcost=0,newcost=0;')
        end = code.index(' /* Synchronous immutable',start)
        costs = code[start:end]
        routine = ('static __attribute__((noinline)) unsigned best_span_cost(const uint8_t *b,unsigned n,bool *split){\n'
                   +costs+' *split=newcost<oldcost;return *split?newcost:oldcost;\n}\n')
        code = code[:start]+' bool split;best_span_cost(b,n,&split);\n'+code[end:]
        code = once(code,'if(newcost<oldcost)count=', 'if(split)count=')
        code = once(code,'static bool span(struct',routine+'static bool span(struct')
        start = code.index(' unsigned old=0,split=0;',code.index('static unsigned span_cost227('))
        end = code.index('\n}',start)
        code = code[:start]+' bool split;return best_span_cost(b,n,&split);'+code[end:]
    path.write_bytes(code.encode())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('base', type=Path)
    p.add_argument('out', type=Path)
    p.add_argument('policy', choices=('advance', 'after-pack', 'after-pause', 'split','small-bg','shared-order','small-shared-cost','credit-only'))
    a = p.parse_args()
    prepare(a.base, a.out, a.policy)
