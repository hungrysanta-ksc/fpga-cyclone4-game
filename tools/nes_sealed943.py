"""Check one additional bounded input read before the previous display retires."""
import argparse
from pathlib import Path
import shutil
from unittest.mock import patch

import nes_chain935 as chain
import nes_discovery942 as prior
from nes_raw506 import once, sha

MODES=('extra','offered','small','handover','poll','ready_poll','geometry','capclass','idleclass')


def work(mode):
    return prior.work('fastfit').parent.parent/'nes-sealed943'/mode


def prepare(mode):
    base=prior.work('fastfit')/'link'
    assert sha(base/'src/obj-nes-100/firmware.stm')=='a22c148abf59e871f7e3e85ce7e3e691030be35890b8bf7d031c76ac1748a6eb'
    link=work(mode)/'link'
    shutil.copytree(base,link)
    path=link/'src/nes_native_runtime165.c'
    code=path.read_text()
    if mode=='idleclass':
        # Replace one unproductive sealed-output pause with useful work on
        # immutable geometry. No extra D1 and no early D3 or credit change.
        anchor=' return nes_cost474_pause(ctx,check,reason,progress,'
        code=once(code,anchor,
            ' if(reason==2 && !progress && !s->prefetch_left && !r->obj_check913 &&\n'
            '    r->state==NES_NATIVE165_RECEIVING && r->next_kind==7){\n'
            '  nes_native913_classify(r);return check(ctx);\n }\n'+anchor)
    elif mode in ('geometry','capclass'):
        # META_END has validated all six counts and frozen OBJ and raster.
        # Later data can invalidate the frame, but cannot change either input to
        # the capacity check. Only prepare() may send D3 after checked END/EA.
        frozen='r->state==NES_NATIVE165_RECEIVING && r->next_kind==7'
        if mode=='capclass':
            frozen+=' && !s->prefetch_left'
        code=once(code,'if(reason==2 && r->state==NES_NATIVE165_COMPLETE)',
            f'if(reason==2 && (r->state==NES_NATIVE165_COMPLETE || ({frozen})))')
    elif mode in ('poll','ready_poll'):
        # Budget exhausted. Prefer polling for the checked display receipt
        # while the next data read must wait for the display lease to retire.
        trigger='!s->prefetch_left'
        if mode=='ready_poll':
            trigger+=' && r->ready183'
        code=once(code,'reason==2 && (r->state==NES_NATIVE165_COMPLETE',
            f'reason==2 && (({trigger}) || r->state==NES_NATIVE165_COMPLETE')
    else:
        code=once(code,'s->prefetch_left=17;reason=2;', 's->prefetch_left=18;reason=2;')
    if mode in ('offered','small'):
        # Only use the last sealed-display credit for an already offered block.
        # The normal poll rechecks CRC, consumes the D1 and confirms the D2.
        test='!r->ready183'
        if mode=='small':
            test+=' || r->status183[5] || r->status183[6]>24'
        code=once(code,'   bool first=',f'   if(reason==2 && s->prefetch_left==1 && ({test}))break;\n   bool first=')
    if mode=='handover':
        # Give the final E0 an opportunity before consuming the extra credit.
        code=once(code,'if(reason!=2 || first)break;','if(reason!=2 || first || s->prefetch_left==1)break;')
    path.write_text(code,newline='\n')


def check_frozen_geometry(mode):
    import json
    from check_nes_game478 import Machine
    from check_nes_sram897 import TRACE

    m=Machine(work(mode)/'link/src',bytes(128))
    layout=m.layout['nes_native165']
    scratch=0x21000000
    m.u.mem_map(scratch,4096)
    blocks=[]
    for tx,reply in json.loads(TRACE.read_bytes())['transactions']:
        opcode=bytes.fromhex(tx)[0]
        if opcode==0xd3:
            break
        if opcode==0xd1:
            blocks.append(bytes.fromhex(reply)[1:-2])
    def field(name):
        return m.u.mem_read(m.state+layout[name],1)[0]
    m.call('nes_native165_reset',[m.state])
    checked=0
    for token,block in enumerate(blocks):
        m.u.mem_write(scratch,block)
        if token==len(blocks)-1:
            before=bytes(m.u.mem_read(m.state,layout['size']))
            assert checked and not m.call('nes_native165_packet',[m.state,token,scratch,len(block)-1])
            assert field('state')!=2
            m.u.mem_write(m.state,before)
        assert m.call('nes_native165_packet',[m.state,token,scratch,len(block)])
        if field('state')==1 and field('next_kind')==7 and not checked:
            m.call('nes_native913_classify',[m.state])
            checked=field('obj_check913')
    assert field('state')==2 and field('obj_check913')==checked and checked in (1,2)
    m.u.mem_write(m.state+layout['obj_check913'],bytes(1))
    m.call('nes_native913_classify',[m.state])
    assert field('obj_check913')==checked
    m.call('nes_native165_reset',[m.state])
    assert field('obj_check913')==0
    return dict(blocks=len(blocks),early_matches_end=True,truncated_end_rejected=True,reset_clears=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof','guards','frozen'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',nargs='?',type=int,choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=p.parse_args()
    tag='943'+a.mode
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        with patch.object(chain,'output',lambda _:prior.ROM):
            chain.replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=work(a.mode),tag=tag)
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        from nes_order938 import empty_next_offer
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(a.mode),925,
            short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    elif a.action=='frozen':
        import json
        result=check_frozen_geometry(a.mode)
        (work(a.mode)/'frozen943.json').write_text(json.dumps(result)+'\n')
    else:
        import check_nes_discovery942 as guards
        with patch.object(guards,'work',work):
            guards.check(a.temp,a.mode,tag=tag,record='safety943.json')
