"""Defer only a non-selected 16-byte diagnostic header across the checked input COMMIT."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_input949 as previous
from nes_credit946 import ROM, base, once, sha

SOURCE = previous.work('stage')
ROOT = SOURCE.parent.parent / 'nes-header950'


def work(mode):
    return ROOT / mode


def prepare(mode):
    expected = json.loads((Path(__file__).resolve().parents[1] /
                           'analysis/input949-results.json').read_bytes())
    assert sha(SOURCE/'link/src/obj-nes-100/firmware.stm') == expected['cases']['cold1']['held_stage']['firmware']
    link = work(mode) / 'link'
    shutil.copytree(SOURCE/'link', link)
    src = link / 'src'
    f = src / 'nes_budget210.c'
    s = f.read_text()
    marker = 'static void record900('
    insert = '''/* Row identity and descriptor were copied at final ACK. Header-only rows
 * have no detail pages. A failed or stale read leaves their valid bit clear. */
static struct row900 *pending950;
static uint32_t start950;
static bool header950(struct row900 *r){
 uint8_t *h=r->wire;
 return page905(h,256) && h[1]==0x95 && (h[2]|h[3]<<8)==r->gen &&
        (!h[5] || !memcmp(h+12,r->descriptor+8,4));
}
void finish_header950(void){
 struct row900 *r=pending950;
 if(!r)return;
 pending950=NULL;
 if(header950(r))r->valid|=4;
 uint32_t elapsed=(nes_cost471_now()-start950)>>9;
 r->probe=elapsed>65535?65535:elapsed;
}
'''
    s = once(s,marker,insert+marker)
    a=s.index(' if(mode900!=3 && page905(page,256))')
    b=s.index('   if((r->valid&3)',a)
    s=s[:a]+''' unsigned score=1+(r->dirty==9 && r->bg==529 && r->obj==14)*4u+
                    (tick>=5616 && tick<=5676);
 uint32_t desc;memcpy(&desc,r->descriptor+2,4);
 unsigned bonus=desc==0x01200040u ? 8 : 0;
 /* A header can add the bonus only for the matching descriptor. Keep
  * any potential detail winner synchronous, even before the first sample. */
 if(mode900!=3 && score+bonus<=log->score && native_runtime165.receiver &&
    native_runtime165.receiver->state==NES_NATIVE165_COMPLETE){
  pending950=r;start950=t;return;
 }
 if(mode900!=3 && header950(r)){
   r->valid|=4;
   if(r->wire[4]==9 && r->wire[5]==4)score+=bonus;
'''+s[b:]
    s=once(s,'page[4]<255 && page[5] && page[5]<63','r->wire[4]<255 && r->wire[5] && r->wire[5]<63')
    s=once(s,'\n  }\n }\ntrace_done:', '\n }\ntrace_done:')
    s=once(s,' latest900=0;', ' pending950=NULL;latest900=0;')
    f.write_text(s,newline='\n')
    f=src/'nes_native_runtime165.c'
    s=once(f.read_text(),'bool nes_runtime165_step(', 'extern void finish_header950(void);\nbool nes_runtime165_step(')
    # Leave the measured D2 window in the old step intact. Flush after the
    # confirmed D2/D0, before replacing its diagnostic pair or issuing E9.
    s=once(s,'  step_begin915=cost_mark471;', '''  uint32_t committed950=nes_cost471_now();
  finish_header950();
  step_begin915=cost_mark471;''')
    s=once(s,'commit_clock915=cost_mark471;', 'commit_clock915=committed950;')
    f.write_text(s,newline='\n')
    if mode in ('fit','simple','bound'):
        # A descriptor-bearing row must have a returned chunk and the same
        # token. A no-tile row has neither. Never bless an empty stale header.
        f=src/'nes_budget210.c'
        code=once(f.read_text(),'(!h[5] || !memcmp(h+12,r->descriptor+8,4))',
                  '(h[5] ? !memcmp(h+12,r->descriptor+8,4) : !r->descriptor[0])')
        if mode=='bound':
            code=once(code,'h[5] ? !memcmp','h[5] ? r->descriptor[0] && !memcmp')
        f.write_text(code,newline='\n')
        f=src/'nes_sink_trace168.c'
        s=f.read_text()
        a=s.index('int nes_sink168_format(')
        s=s[:a]+'''#include "nes_cost471.h"
extern int nes_hexline512(char *,unsigned,int,const uint8_t *,unsigned);
int nes_sink168_format(char *text,unsigned capacity){
 static const char header[]="sink_trace_valid=0\\nsink_trace_ack_valid=0\\nsink_trace_mismatch_hex=00\\nsink_trace_request_hex=";
 static const char middle[]="sink_trace_ack_hex=";
 const unsigned needed=sizeof(header)-1+32+1+sizeof(middle)-1+24+1;
 if(!text || capacity<=needed)return -1;
 int n=nes_packed828(text,capacity,0,"sink_trace_valid=%u\\nsink_trace_ack_valid=%u\\nsink_trace_mismatch_hex=%02x\\nsink_trace_request_hex=",
   nes_sink_trace168.valid,nes_sink_trace168.ack_valid,nes_sink_trace168.mismatch);
 n=nes_hexline512(text,capacity,n,nes_sink_trace168.request,16);
 n=nes_packed828(text,capacity,n,"sink_trace_ack_hex=");
 return nes_hexline512(text,capacity,n,nes_sink_trace168.ack,12);
}
'''
        f.write_text(s,newline='\n')
    if mode in ('simple','bound'):
        from pack_nes_header950 import reuse
        reuse(src)
    if mode in ('packed','fit'):
        from pack_nes_header950 import pack
        print('Post-session formats and maximum pair depth:',pack(src))


def replay(temp,mode,phase,cache):
    from replay_nes_strip869 import dense
    from test_nes_receive649 import admission
    chain=base.prev.chain
    rt=dense.joint.Runtime
    with patch.object(rt,'offer_input',admission(rt.offer_input)),patch.object(chain,'output',lambda _:ROM):
        chain.replay(temp,'final',phase,cache,'bounded',work_arm=work(mode),tag='950'+mode)


def guards(temp,mode):
    from check_nes_supply905_arm import run
    from nes_order938 import empty_next_offer
    from nes_deadline947 import check_obj_recovery
    import nes_return920
    arm=work(mode)
    run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',arm,925,
        short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    with patch.object(nes_return920,'client',lambda _:ROM):
        nes_return920.guards(temp,'first',tag='950'+mode,destination=arm/'final-guards.json')
    check_obj_recovery(temp,mode,work=work,prefix='950')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','guards'))
    p.add_argument('mode',choices=('split','packed','fit','simple','bound'))
    p.add_argument('temp',type=Path)
    p.add_argument('phase',nargs='?',type=int,choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='guards':
        guards(a.temp,a.mode)
    else:
        replay(a.temp,a.mode,a.phase,a.cache)
