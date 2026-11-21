"""Prepare the MMC915 physical demo release from the selected 913 ARM and 914I board."""
import argparse
from pathlib import Path
from types import SimpleNamespace

from nes_overlap913 import work
from nes_raw506 import once
from prepare_nes_supply905 import PROBES, QUARTUS, image, rename_edition

WORK=PROBES/'nes-trial915'
PARENT=work('idle')


def patch_arm(step=False):
    src=PARENT/'link/src'
    dest=WORK/('patch-step' if step else 'patch')
    rename_edition(src,dest,907,915)
    h=once((src/'nes_frame900.h').read_text(),'uint16_t displayed55;', 'uint16_t displayed55,commit_age915,query_age915;')
    if step:h=once(h,'query_age915;', 'query_age915,step_span915;')
    (dest/'nes_frame900.h').write_text(once(h,'void input900','extern uint32_t commit_clock915,step_begin915;\nextern uint16_t commit_gen915;\nvoid input900'),newline='\n')
    p=(src/'nes_native165.c').read_text()
    p=once(p,' /* D2 replies before retirement.', ''' if(s->state==NES_NATIVE165_COMMITTED){
  commit_clock915=nes_cost471_now();commit_gen915=s->generation;
 }
 /* D2 replies before retirement.''')
    if step:
        runtime=(src/'nes_native_runtime165.c').read_text()
        runtime='#include "nes_frame900.h"\n'+once(runtime,' if(r->state==NES_NATIVE165_COMMITTED){\n  cost_mark471=nes_cost471_now();',
            ' if(r->state==NES_NATIVE165_COMMITTED){\n  step_begin915=cost_mark471;\n  cost_mark471=nes_cost471_now();\n  commit_clock915=cost_mark471;commit_gen915=r->generation;')
        (dest/'nes_native_runtime165.c').write_text(runtime,newline='\n')
    else:(dest/'nes_native165.c').write_text(p,newline='\n')
    s=once((src/'nes_budget210.c').read_text(),'edition=907','edition=915')
    s=once(s,'unsigned char mode900;', 'uint32_t commit_clock915;uint16_t commit_gen915;\nunsigned char mode900;')
    s=once(s,'!r->dirty && r->bg==528 && r->obj==45','r->dirty==9 && r->bg==529 && r->obj==14')
    s=once(s,'page[4]==31 && page[5]==8 && r->descriptor[2]==32 && !r->descriptor[3] &&\n      r->descriptor[4]==0xc0 && r->descriptor[5]==3',
           'page[4]==9 && page[5]==4 && descriptor==0x01200040u')
    s=once(s,'   unsigned score=1;', '   uint32_t descriptor;memcpy(&descriptor,r->descriptor+2,4);\n   unsigned score=1;')
    s=once(s,'tick>=5644 && tick<=5704','tick>=5616 && tick<=5676')
    s=once(s,'    log->selected=0;', '    unsigned query_age=(nes_cost471_now()-t)>>9;\n    log->selected=0;')
    s=once(s,'    log->selected=log->used;', '''    log->commit_age915=commit_gen915==r->gen?(t-commit_clock915)>>9:65535;
    log->query_age915=query_age;
    log->selected=log->used;''')
    if step:
        s=once(s,'uint32_t commit_clock915;', 'uint32_t commit_clock915,step_begin915;')
        s=once(s,'    unsigned query_age=(nes_cost471_now()-t)>>9;\n','')
        s=once(s,'    log->query_age915=query_age;', '    log->step_span915=(commit_clock915-step_begin915)>>9;')
    (dest/'nes_budget210.c').write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['patch','image','wire','replay','guards'])
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    p.add_argument('--cold',action='store_true')
    p.add_argument('--step',action='store_true')
    a=p.parse_args()
    target=WORK.parent/'nes-trial915-step' if a.step else WORK
    prefix='915step' if a.step else '915'
    if a.action=='patch':patch_arm(a.step)
    elif a.action=='image':image(SimpleNamespace(board=a.temp/'nes-port914I/nes-trial816-board914',out=a.temp/'nes-trial915-image',quartus=QUARTUS,number='914'))
    elif a.action=='guards':
        from check_nes_supply905_arm import run
        run(a.temp,target,915)
    elif a.action=='wire':
        from fixture_nes_port914 import FixtureLink, fixture, peer, monitor, patch, OUT
        with patch.object(peer,'PeerLink',FixtureLink),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
            peer.compare(a.temp,a.phase,a.cold,True,edition=915,work_arm=target,run_id=prefix+'wire')
        for g in ((912,) if a.cold else (910,911,912)):
            fixture(a.temp,a.phase,a.cold,g,prefix+'wire')
    else:
        from replay_nes_head914 import replay
        replay(a.temp,a.phase,a.cold,'I',arm=target,edition=915,wire_tag=prefix+'wire',run_id=prefix+'final',transcript_dir=a.temp/('nes-trial'+prefix+'-rtl'))
