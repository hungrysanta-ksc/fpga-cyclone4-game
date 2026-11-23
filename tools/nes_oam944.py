"""Schedule ready bulk ahead of a repeated OAM fill on the linked 943 receiver."""
import argparse
from pathlib import Path
import shutil
from unittest.mock import patch

import nes_sealed943 as prev
from nes_raw506 import once, sha

MODES=('credit','prefix','drain','reserve','single','one','swap','verified','checked','tail','firstbg','twobanks','repeat','live','livebg','active','pair','smallbg','bgslot','bgcredit','live16','live16_once')


ROOT=prev.work('capclass').parent.parent/'nes-oam944'


def work(mode):
    return ROOT/mode


def prepare(mode):
    original=prev.work('capclass')/'link'
    assert sha(original/'src/obj-nes-100/firmware.stm')=='d692bd9396a4a78d03560a3bd3bdd04a7c4c3e74cf158da4693c09a8af5c2cc0'
    link=work(mode)/'link'
    shutil.copytree(original,link)
    path=link/'src/nes_native_sink165.c'
    path.write_text(schedule(path.read_text(),mode),newline='\n')


def schedule(code,mode):
    last='s->plan->window->last[1]'
    query='nes_plan200_progress(s->plan,NES_ORDINARY553)'
    wait='wait_map880(s->plan->window,12)'

    if mode in ('credit','reserve'):
        gate=f'{last}==4'
        if mode=='reserve':
            gate+=' && (uint16_t)(s->plan->window->sent-s->plan->window->retired)==4'
        anchor=' /* Let an already submitted OBJ return before issuing the OAM fill.'
        return once(code,anchor,f''' if(op==8 && s->plan && s->plan->window && {gate}){{
  bool room;
  if(!nes_window532_room(s->plan->window,&room))return fail(s,5);
  if(room && !nes_plan200_progress(s->plan,NES_ORDINARY553))return fail(s,5);
 }}
'''+anchor)

    if mode in ('live','livebg'):
        # Return prefix credit before the original descriptor selection.
        mark=' if(first&&!span(s,4,0,b,first))return false;'
        gate='first && s->plan && !s->plan->finished && s->plan->window'
        if mode=='livebg':
            gate+=' && !s->plan->bulk[1]'
        return once(code,mark,mark+f'\n if({gate} && !wait_map880(s->plan->window,1))return fail(s,5);')

    # Which previous head can justify a checked credit wait before OAM?
    old='s->plan->window->last[0]==7 && s->plan->window->last[1]==1'
    gate=f'({last}==1 || {last}==4)'
    if mode in ('prefix','drain'):
        gate=f'(({old}) || {last}==4)'
    elif mode in ('active','pair'):
        gate=f'({last}==1 || (!s->plan->finished && {last}==4))'
    elif mode in ('firstbg','twobanks','repeat'):
        gate=f'(({last}==1 && s->plan->window->last[0]==7) || ({last}==4 && !s->plan->bulk[1]))'
    elif mode in ('smallbg','bgslot','bgcredit'):
        # OBJ sizes are multiples of 32; exactly 16B identifies one BG.
        gate=f'({last}==1 || ({last}==4 && s->plan->bulk[2]==16 && !s->plan->bulk[3]))'
    elif mode in ('live16','live16_once'):
        # Spending credit on OAM cannot uncover another tile after plan FINISH.
        gate=f'({last}==1 || ({last}==4 && !s->plan->finished && s->plan->bulk[2]==16 && !s->plan->bulk[3]))'
    code=once(code,old+' &&',gate+' &&')

    if mode=='swap':
        code=once(code,wait,f'({last}==4 || {wait})')
    elif mode!='drain':
        limit='1' if mode in ('one','checked','bgslot','live16_once') else f'{last}==4?1:12'
        code=once(code,wait,f'wait_map880(s->plan->window,{limit})')

    # The two-batch control suppresses a second E8 even if ready changed
    # during E0. Every alternative still uses the ordinary checked poll.
    before='(!(s->plan->sent>2) || '+query+')'
    if mode in ('single','one','swap','prefix','drain'):
        return code
    after=query
    if mode=='pair':
        after=f'({query} && (!s->plan->bulk_pending || {query}))'
    elif mode=='repeat':
        after=f'({query} && (!s->plan->bulk_pending || !s->plan->bulk[1] || s->plan->bulk[2]!=32 || s->plan->bulk[3] || {query}))'
    if mode in ('tail','firstbg','repeat','bgcredit'):
        after=f'(({last}!=4 && s->plan->sent<=2) || {after})'
    return once(code,before,after)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','proof','guards','frozen'))
    parser.add_argument('mode',choices=MODES)
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',nargs='?',type=int,choices=(1,2))
    parser.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=parser.parse_args()
    tag='944'+a.mode
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        with patch.object(prev.chain,'output',lambda _:prev.prior.ROM):
            prev.chain.replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=work(a.mode),tag=tag)
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        from nes_order938 import empty_next_offer
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(a.mode),925,
            short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    elif a.action=='frozen':
        import json
        with patch.object(prev,'work',work):
            (work(a.mode)/'frozen944.json').write_text(json.dumps(prev.check_frozen_geometry(a.mode))+'\n')
    else:
        import check_nes_discovery942 as guards
        with patch.object(guards,'work',work):
            guards.check(a.temp,a.mode,tag=tag,record='safety944.json')
