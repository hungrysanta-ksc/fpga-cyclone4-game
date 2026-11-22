"""Compare bounded next-input service at the sealed display barrier."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_chain935 import replay
from nes_head939 import work as prior
from nes_order938 import empty_next_offer
from nes_oam937 import guards
from nes_raw506 import once, sha

MODES=('control','idle','retry','both','begin','idlebegin','pairbegin','decode','idledecode','begindecode','handoff','handoffdecode')


def work(mode):
    return prior('tile').parent.parent/'nes-input940'/mode


def prepare(mode):
    source=prior('tile')/'link'
    assert sha(source/'src/obj-nes-100/firmware.stm')=='97d217e3fa14a0293c9c9dd404ca3902566497b5532cd98a4b090ff5ce70b596'
    link=work(mode)/'link'
    shutil.copytree(source,link)
    # All arms, including the control, use the same tested six marker encodings.
    menu='src/nes_menu_diagnostic.c'
    shutil.copyfile(prior('marker')/'link'/menu,link/menu)
    path=link/'src/nes_native_runtime165.c'
    s=path.read_text()
    if mode in ('idle','both','idlebegin','idledecode','handoff','handoffdecode'):
        s=once(s,'reason==2 && r->state==NES_NATIVE165_COMPLETE ? 0',
                 'reason==2 && (r->state==NES_NATIVE165_COMPLETE || r->state==NES_NATIVE165_IDLE) ? 0')
    if mode in ('retry','both','pairbegin'):
        s=once(s,'  while(s->prefetch_left','  bool retry_idle=(reason==2);\n  while(s->prefetch_left')
        s=once(s,'if(r->next_token==before)break;',
               '''if(r->next_token==before){
    if(!retry_idle || r->state!=NES_NATIVE165_IDLE)break;
    retry_idle=false;
    continue;
   }''')
    if mode in ('begin','idlebegin','pairbegin','begindecode'):
        # BEGIN receipt gates planner entry. Keep every real E0/identity
        # check; only remove the quiet interval after an outstanding BEGIN.
        s=once(s,'s->plan.tile_service || s->transport.last[1]==1',
                 's->plan.tile_service || s->transport.last[1]==1 || s->transport.last[0]==1')
    if mode in ('handoff','handoffdecode'):
        # Once a real first D2 is confirmed, give the previous display one
        # E0 opportunity. The remaining input credit stays with its owner.
        s=once(s,'   uint16_t before=r->next_token;',
               '   bool first=(r->state==NES_NATIVE165_IDLE);\n   uint16_t before=r->next_token;')
        s=once(s,'if(reason!=2)break;','if(reason!=2 || first)break;')
    if mode in ('decode','idledecode','begindecode','handoffdecode'):
        receiver=link/'src/nes_native165.c'
        old='uint64_t value=0;for(unsigned j=0;j<width;j++)value=(value<<8)|p[pos++];'
        # Loads are limited by the existing n-pos >= width check. memcpy
        # supports unaligned packet records; the wire representation is big endian.
        code=once(receiver.read_text(),old,"""uint64_t value=0;
  while(width>=4){
   uint32_t word; memcpy(&word,p+pos,4);
   value=(value<<32)|__builtin_bswap32(word);pos+=4;width-=4;
  }
  while(width--){value=(value<<8)|p[pos++];}""")
        receiver.write_text(code,newline='\n')
    path.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof','dispatch','guards'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,nargs='?',choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=p.parse_args()
    arm=work(a.mode)
    tag='940'+a.mode
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=arm,tag=tag)
    elif a.action=='guards':
        guards(a.temp,tag,arm)
    elif a.action=='dispatch':
        import check_nes_order938
        with patch.object(check_nes_order938,'work',work):
            check_nes_order938.run(a.mode)
    else:
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',arm,925,
            short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
