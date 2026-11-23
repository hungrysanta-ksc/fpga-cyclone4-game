"""Replay changes to short OBJ discovery against the fixed 938 ARM and 935 ROM."""
import argparse
import shutil
from pathlib import Path

from nes_chain935 import replay
from nes_order938 import empty_next_offer, work as base
from nes_oam937 import guards
from nes_raw506 import once, sha

MODES=('credit','pace','words','joint','shortword','tile','tail','marker','retired','table','prefix')
PACKED_MARKERS=('marker','retired','table','prefix')
SHORT_OBJ='(s->transport.last[0]==7 && s->plan.bulk[2]==32 && !s->plan.bulk[3])'
OBJ_SECTION='s->transport.last[1]==1'
# Conditions only suppress the timed quiet period. The normal service/STOP
# check and the next transfer's independent receipt checks still run.
FAST_POLL={
    'pace':SHORT_OBJ,'joint':SHORT_OBJ,'marker':SHORT_OBJ,
    'shortword':r'(s->transport.last[0]==7 && !memcmp(s->plan.bulk+2,"\040",2))',
    'tile':OBJ_SECTION,'prefix':OBJ_SECTION,
    'tail':'(s->transport.last[1]==1 || s->transport.last[1]==5)',
    'retired':'((s->transport.last[1]==1) || (!reason && s->plan.ending && s->plan.bulk_valid && !s->plan.bulk_pending))',
    'table':'(s->transport.last[1]==1 || (!reason && s->transport.last[1]==5 && s->plan.ending))',
}



def work(mode):
    return base('fit').parent.parent/'nes-head939'/mode


def prepare(mode):
    source=base('fit')/'link'
    assert sha(source/'src/obj-nes-100/firmware.stm')=='0f3c4e544187fcaab1966aae22709a3857dcbcc2c4ad89ba65df2c5aaec67723'
    link=work(mode)/'link'
    shutil.copytree(source,link)
    sink=link/'src/nes_native_sink165.c'
    text=sink.read_text()
    if mode=='credit':
        text=once(text,'at>=128 && age<3','at>=128 && !age')
    if mode not in ('credit','pace'):
        # Equal word repetitions are exactly a two-byte periodic sequence.
        # memcmp permits unaligned sources and never examines the next packet.
        text=once(text,'unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}\n  if(i==n)',
                  'if(!data || !memcmp(data,data+2,n-2))')
    if mode in FAST_POLL:
        runtime=link/'src/nes_native_runtime165.c'
        urgent=FAST_POLL[mode]
        old='s->plan.tile_service ? 0 : 84u*128u'
        runtime.write_text(once(runtime.read_text(),old,
            f'(s->plan.tile_service || {urgent}) ? 0 : 84u*128u'),newline='\n')
    if mode in PACKED_MARKERS:
        menu=link/'src/nes_menu_diagnostic.c'
        code=once(menu.read_text(),'geometry_delta[]={0,1,2,26,27,28}','marker_mode[]={4,1,2,8,16,24}')
        code=once(code,'sizeof geometry_delta','sizeof marker_mode')
        code=once(code,'return 384+geometry_delta[i]','return marker_mode[i]')
        code=once(code,'mode900=selected>=410?(unsigned char)(selected-409):0;',
                  'mode900=selected>>3;')
        code=once(code,'nes_boot_probe798=mode900?0:(unsigned char)(selected-384);',
                  'nes_boot_probe798=selected&3;')
        menu.write_text(code,newline='\n')
    if mode=='prefix':
        header=link/'src/nes_plan_service200.h'
        header.write_text(once(header.read_text(),'NES_HDMA554};','NES_HDMA554,NES_OAM_PREFIX939};'),newline='\n')
        text=once(text,'section==2?NES_MAP553:NES_ORDINARY553',
                  'section==2?NES_MAP553:section==4 && !at?NES_OAM_PREFIX939:NES_ORDINARY553')
        plan=link/'src/nes_plan_service200.c'
        code=once(plan.read_text(),'if((mode==NES_MAP553 || mode==NES_ORDINARY553) &&',
                  'if((mode==NES_MAP553 || mode==NES_ORDINARY553 || mode==NES_OAM_PREFIX939) &&')
        code=once(code,'(uint16_t)(p->window->sent-p->window->retired)<=2)return true;',
                  '(uint16_t)(p->window->sent-p->window->retired)<=(mode==NES_OAM_PREFIX939?3:2))return true;')
        plan.write_text(code,newline='\n')
    sink.write_text(text,newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','proof','guards','dispatch'))
    parser.add_argument('mode',choices=MODES)
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',type=int,nargs='?',choices=(1,2))
    parser.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=parser.parse_args()
    arm=work(a.mode)
    tag='939'+a.mode
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=arm,tag=tag)
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',arm,925,
            short_header=True,order=empty_next_offer,
            marker_values=(4,8,16,24) if a.mode in PACKED_MARKERS else (384,410,411,412))
    elif a.action=='dispatch':
        from unittest.mock import patch
        import check_nes_order938
        with patch.object(check_nes_order938,'work',work):
            check_nes_order938.run(a.mode)
    else:
        guards(a.temp,tag,arm)
