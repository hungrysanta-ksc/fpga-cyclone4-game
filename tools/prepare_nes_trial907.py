"""Build the MMC907 measurement edition on the fitted 906 board."""
import argparse
from pathlib import Path
from types import SimpleNamespace
from prepare_nes_supply905 import ROOT, PROBES, QUARTUS, image, rename_edition
from nes_raw506 import once

WORK=PROBES/'nes-trial907'
BASE=PROBES/'nes-supply905/link'

def patch_arm():
    src=BASE/'src'
    dest=WORK/'patch'
    rename_edition(src,dest,905,907)
    hdr=(src/'nes_frame900.h').read_text()
    (dest/'nes_frame900.h').write_text(once(hdr,'sample[320][8];','sample[320][8]; uint16_t displayed55;'),newline='\n')
    s=once((src/'nes_budget210.c').read_text(),'edition=905','edition=907')
    s=once(s,' record900(s->frame_start,v);',
           ' if(elapsed>=5500 && elapsed<6000)++log900p->displayed55;\n record900(s->frame_start,v);')
    a=s.index('   unsigned age=')
    b=s.index('   if((r->valid',a)
    s=s[:a]+'''   /* Score the recorded MMC905 workload independently of the candidate's speed. */
   unsigned score=1;
   if(!r->dirty && r->bg==528 && r->obj==45)score+=4;
   if(page[4]==31 && page[5]==8 && r->descriptor[2]==32 && !r->descriptor[3] &&
      r->descriptor[4]==0xc0 && r->descriptor[5]==3)score+=8;
   if(tick>=5644 && tick<=5704)++score;
'''+s[b:]
    s=once(s,'score>=(int)log->score','score>log->score')
    (dest/'nes_budget210.c').write_text(s,newline='\n')

def make_image(temp):
    image(SimpleNamespace(board=temp/'nes-trial816-board906',out=temp/'nes-trial907-image',
                          quartus=QUARTUS,number='906'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('patch')
    sub.add_parser('image').add_argument('temp',type=Path)
    arm=sub.add_parser('check-arm')
    arm.add_argument('game',type=Path)
    arm.add_argument('reference_trace',type=Path)
    sub.add_parser('replay').add_argument('temp',type=Path)
    a=p.parse_args()
    if a.action=='patch':patch_arm()
    elif a.action=='image':make_image(a.temp)
    elif a.action=='check-arm':
        from check_nes_supply905_arm import run
        from check_nes_selector907 import verify
        run(a.game,WORK,907)
        verify(a.reference_trace)
    else:
        from replay_nes_peer906 import compare
        for phase in (1,2):
            for cold in (False,True):compare(a.temp,phase,cold,True,edition=907,work_arm=WORK)
