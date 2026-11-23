"""Compare checked OBJ retirement schedules on the final 945 ARM and client."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_handoff945 import base, work as work945
from nes_raw506 import once, sha

BASE=work945('warm_header')
ROM=base.prev.prior.ROM
ROOT=BASE.parent.parent/'nes-credit946'
MODES=('section','short','short_once','descriptor','checked','service','objfit','settle','shortfit','retire','objsettle','shortsettle','creditonly','objguard','formats')


def work(mode):
    return ROOT/mode


def prepare(mode):
    link=work(mode)/'link'
    assert sha(BASE/'link/src/obj-nes-100/firmware.stm')=='4b6216cc2ceab858a1ffed773e762160334985d29bbd1f81d8b5c97f3cfa847e'
    shutil.copytree(BASE/'link',link)
    if mode=='formats':
        from pack_nes_formats946 import compact
        assert compact(link/'src')>=24
        return
    if mode in ('descriptor','checked'):
        path=link/'src/nes_plan_service200.c'
        code=path.read_text()
        # A short OBJ may physically release its aperture before its queue head retires.
        # Look at E8 first; the existing complete485 still gates the next E1.
        gate='p->bulk[1] && p->bulk[2]==64 && !p->bulk[3]'
        if mode=='checked':
            gate+=' && p->ending'
        code=once(code,'if(p->bank_history==2 && !complete485(p))',
                  f'if(p->bank_history==2 && !({gate}) && !complete485(p))')
    elif mode=='short_once':
        path=link/'src/nes_sink_window184.c'
        code=path.read_text()
        # The same STOP/deadline service runs while a single OBJ is still owned.
        pivot='  if(!wait474(s,s->last[0]==3?2:1,s->retired!=before))return false;'
        code=once(code,pivot,'''  if(s->last[1]==1 && i==0 && !s->guard(s->ctx))return fail(s,2);
'''+pivot)
    else:
        path=link/'src/nes_native_runtime165.c'
        code=path.read_text()
        quiet='(s->plan.tile_service || (s->transport.last[1] & ~4u)==1) ? 0 : 84u*128u'
        if mode in ('section','objfit','objsettle','objguard'):
            updated='(s->plan.tile_service || (s->transport.last[1] & ~4u)==1) ? (s->transport.last[1]==1 ? 168u : 0) : 84u*128u'
        elif mode=='creditonly':
            updated=quiet.replace('? 0 :','? (reason==1 ? 168u : 0) :')
        elif mode=='settle':
            updated=quiet.replace('? 0 :','? 168u :')
        elif mode=='retire':
            updated=quiet.replace('? 0 :','? (progress ? 0 : 168u) :')
        elif mode=='service':
            updated='(s->plan.tile_service || (s->transport.last[1] & ~4u)==1) ? (s->plan.tile_service ? 168u : 0) : 84u*128u'
        else:
            updated='(s->plan.tile_service || (s->transport.last[1] & ~4u)==1) ? ((s->transport.last[1]==1 && s->plan.bulk[2]==64 && !s->plan.bulk[3]) ? 168u : 0) : 84u*128u'
        if mode=='objguard':
            updated=updated.replace('168u','84u*4u')
        code=once(code,quiet,updated)
    path.write_text(code,newline='\n')
    if mode in ('objsettle','shortsettle','creditonly','objguard'):
        from pack_nes_formats946 import compact
        assert compact(link/'src')>=24
    if mode in ('settle','shortfit','objfit','retire'):
        path=link/'src/nes_sink_window184.c'
        previous='p[0]!=2&&p[0]!=4&&p[0]!=5&&p[0]!=6&&p[0]!=8&&(unsigned)(p[0]-9)>1&&p[0]!=7'
        predicate='p[0]!=2&&(unsigned)(p[0]-4)>6'
        assert all((i in (2,4,5,6,7,8,9,10))==(i==2 or 4<=i<=10) for i in range(256))
        path.write_text(once(path.read_text(),previous,predicate),newline='\n')


def run(action,mode,temp,phase,cache):
    if action=='prepare':
        prepare(mode)
    elif action=='replay':
        with patch.object(base.prev.chain,'output',lambda _:ROM):
            base.prev.chain.replay(temp,'final',phase,cache,'bounded',work_arm=work(mode),tag='946'+mode)
    elif action=='receipt':
        import check_nes_handoff945 as previous
        with patch.object(previous,'work',lambda _:work(mode)):
            previous.receipt_checks('warm_header')
    elif action=='proof':
        from check_nes_supply905_arm import run as proof
        from nes_order938 import empty_next_offer
        proof(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(mode),925,
              short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    else:
        import check_nes_discovery942 as checks
        with patch.object(checks,'work',work):
            checks.check(temp,mode,tag='946'+mode,record='safety946.json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof','guards','receipt'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,nargs='?',choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=p.parse_args()
    run(a.action,a.mode,a.temp,a.phase,a.cache)
