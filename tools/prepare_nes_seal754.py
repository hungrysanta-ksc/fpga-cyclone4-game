# SPDX-License-Identifier: MIT
"""Prepare independent input lookahead and early section-5 output experiments on 753."""
import argparse
from pathlib import Path

from nes_raw506 import once, sha


def prepare(base, out, policy):
    assert sha(base/'src/obj-nes-100/firmware.stm') == '192cf5becb19bb58ede0be25be73d91e4c1fee1f836eadabcb9999ac2af929a6'
    out.mkdir(parents=True, exist_ok=False)
    if policy == 'shared':
        name = 'nes_native_runtime165.c'
        source = (base/'src'/name).read_text()
        start = source.index('   if(!s->prefetch_left && s->plan.bank_history==2')
        end = source.index('\n   }',start)+5
        source = source[:start]+"""   if(extra){
    if(!r->ready183 || r->next_kind!=0)s->prefetch_left=0;
   }else if(!s->prefetch_left && s->plan.bank_history==2 && r->ready183 &&
            (r->status183[5] || r->status183[6]>=128)){
    extra=true;s->prefetch_left=6;
   }"""+source[end:]
        source = once(source,'  while(s->prefetch_left','  bool extra=false;\n  while(s->prefetch_left')
        (out/name).write_text(source,encoding='utf8',newline='\n')
    if policy in ('geometry', 'both'):
        name = 'nes_native_runtime165.c'
        source = (base/'src'/name).read_text()
        old = '''    if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
    if(!check(ctx))return false;'''
        # Only the large checked eighth head qualifies. Spend up to five more
        # geometry credits, stopping on the first non-geometry or unready head.
        source = once(source, old, '''    for(unsigned left=6;left--;){
     uint16_t token=r->next_token;
     if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
     if(!check(ctx))return false;
     if(r->next_token==token || !r->ready183 || r->next_kind!=0)break;
    }''')
        (out/name).write_text(source, encoding='utf8', newline='\n')
    if policy in ('section', 'both'):
        name = 'nes_native_sink165.c'
        source = (base/'src'/name).read_text()
        scroll = ' if(!span(s,5,0,p->hdma,p->hdma_size))return false;'
        # This immutable scroll prefix already has a section and explicit
        # offset. The checked consumer can stage it independently of map, OAM
        # and raw. Only SEAL can publish it.
        source = once(source, scroll+'\n if(p->patch_count){', ' if(p->patch_count){')
        anchor = ' if(!map527(s,p,r->map_upload,false))return false;'
        source = once(source, anchor, scroll+'\n'+anchor)
        (out/name).write_text(source, encoding='utf8', newline='\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--policy',choices=('geometry','section','both','shared'),required=True)
    a=p.parse_args()
    prepare(a.base,a.out,a.policy)
