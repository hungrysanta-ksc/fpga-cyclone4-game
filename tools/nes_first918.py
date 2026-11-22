"""Pair the checked zero-slot record with the first allocated OBJ slot."""
import argparse
import inspect
import shutil
import textwrap
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from nes_issue917 import ARM, OUT, PAIR, PROBES, monitor, peer
from nes_raw506 import once, sha
from fixture_nes_port914 import FixtureLink, fixture
from test_nes_raw506_joint import Link


def work(mode):
    return PROBES / ('nes-first918-' + mode)


def prepare(mode):
    assert sha(ARM/'link/src/obj-nes-100/firmware.stm')=='98564fcd0f24e3d61eaccee021021a04fd48c45252bf14a676f79fa214e118a7'
    link=work(mode)/'link'
    shutil.copytree((PAIR if mode=='joined' else ARM)/'link',link)
    src=link/'src'
    service=src/'nes_plan_service200.c'
    original=service.read_text()
    at=' if(!append(p,q))return false;'
    if mode=='single':
        predicate='q->kind==2'
    else:
        predicate='q->kind==1 && p->count==2 && p->buffer[4]==0x82'
    service.write_text(once(original,at,at+'''
 /* The owned records are complete. Use the regular checked E9 and E8;
  * never synthesize a token or grant consumer credit here. */
 if(p->bank_history==2 && !p->sent && '''+predicate+'''){
  uint8_t flags;
  return nes_plan549_first(p) && poll(p,&flags,NES_PLAN215_FLUSH);
 }'''),newline='\n')
    if mode in ('early','joined'):
        planner=src/'nes_planner211.c'
        s=planner.read_text()
        start=s.index(' /* No callback retains scratch pointers;')
        stop=s.index(' if(p->scroll_issued && resident->finish_obj',start)
        body=s[start:stop]
        loop=body[body.index(' for(unsigned i=0;i<128;i++)'):body.index(' /* BG allocation')]
        ranks=body[body.index(' /* Compact fragments already carry'):]
        helper='''static bool objects918(const struct nes_native165 *s,struct nes_native_video165 *p,
                       struct nes_resident211 *resident,unsigned palettes){
 /* OAM and CGRAM are cleared on planner entry. The BG pass uses neither.
  * Keep rank and depth in CGRAM until palette construction overwrites it. */
 _Static_assert(sizeof(p->cgram)>=448,"rank and depth scratch");
 uint8_t *rank_used=p->cgram,*evaluation=rank_used+224;
'''+loop+ranks+' return true;\n}\n'
        if mode=='joined':
            helper=helper.replace('unsigned palettes){','unsigned palettes,uint8_t *rank_used){').replace(
                'uint8_t *rank_used=p->cgram,*evaluation=rank_used+224;',
                'uint8_t *evaluation=rank_used+224; memset(rank_used,0,448);')
        s=s[:start]+''' if(!early_obj && !objects918(s,p,resident,palettes))return false;
'''+s[stop:]
        s=once(s,'static bool build211(',helper+'static bool build211(')
        s=once(s,' /*226: exceptions', ''' bool early_obj=inherit && !resident->map_stale[resident->target];
 if(early_obj && !objects918(s,p,resident,palettes))return false;
 /*226: exceptions''')
        if mode=='joined':
            s=once(s,'bool early_obj=inherit &&','bool early_obj=p->patch_count==1 && inherit &&')
            s=once(s,'if(early_obj && !objects918(s,p,resident,palettes))',
                     'if(early_obj && !objects918(s,p,resident,palettes,p->cgram))')
            s=once(s,'if(!early_obj && !objects918(s,p,resident,palettes))',
                     'if(!early_obj && !objects918(s,p,resident,palettes,(uint8_t *)p->bg_keys+3072))')
        planner.write_text(s,newline='\n')
    # One full drain retains the same checked receipt (916 control).
    sink=src/'nes_native_sink165.c'
    if mode!='joined':
        sink.write_text(once(sink.read_text(),'   for(unsigned sample=0;sample<4;sample++)\n    if(!nes_window184_drain',
                            '   if(!nes_window184_drain'),newline='\n')


def close_zero():
    # Same write/SEAL boundary as the host RTL. Charge the existing bulk RAM
    # write latency and the publication edge even when no next plan exists.
    original=Link.advance
    s=textwrap.dedent(inspect.getsource(original))
    at='        if not self.todo:return'
    s=once(s,at,'''        if self.open and not self.open['kind'] and self.open['slot']==0 and len(self.open['data'])==16:
            edge=self.producer_clock+1
            if now<edge:return
            self.boundary_clock=edge
            self.publish()
'''+at)
    ns={}
    exec(s,original.__globals__,ns)
    return patch.object(Link,'advance',ns['advance'])


def board(temp):
    src=temp/'nes-port914I/nes-trial816-board914'
    dest=work('single')/'rtl'
    dest.mkdir(exist_ok=True)
    for name in ('nes_domain_reset124','nes_native_mailbox206','nes_plan_batch206','nes_e9_scan914',
                 'nes_obj_capture611','nes_chr_cache611','nes_tile205','nes_native_arbiter165',
                 'nes_e9_rows914','nes_source_tile192','nes_rom_physical','nes_bulk_aperture188','nes_tile_bulk206'):
        f=src/(name+'.sv')
        if name=='nes_tile_bulk206':
            s=once(f.read_text(),"next_slot<={1'b0,wslot}+11'd1;state<=CHECK;",
                   "next_slot<={1'b0,wslot}+11'd1;state<=(!wkind && wslot==0)?SEAL:CHECK;")
            (dest/f.name).write_text(s,newline='\n')
        else:
            shutil.copyfile(f,dest/f.name)


def replay(temp, phase, cold, mode):
    with (close_zero() if mode=='single' else nullcontext()),patch.object(peer,'PeerLink',FixtureLink),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
        peer.compare(temp,phase,cold,True,edition=915,work_arm=work(mode),run_id='918'+mode)
    if mode=='single':
        for g in (908,912):
            fixture(temp,phase,cold,g,'918single')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','guards','board'))
    p.add_argument('mode',choices=('pair','early','single','joined'))
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    p.add_argument('--cold',action='store_true')
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='board':
        board(a.temp)
    elif a.action=='replay':
        replay(a.temp,a.phase,a.cold,a.mode)
    else:
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(a.mode),915)
