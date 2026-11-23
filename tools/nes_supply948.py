"""Retain contiguous OBJ destinations while advancing the first zero tile."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_deadline947 as prior
from nes_credit946 import ROM, base, once, sha

SOURCE=prior.work('pressure_seal')
MODES=('zero','run','group','zero_fit','cut','half_page')


def work(mode):
    return SOURCE.parent.parent/'nes-supply948'/mode


def prepare(mode):
    expected=json.loads((Path(__file__).resolve().parents[1]/'analysis/deadline947-results.json').read_bytes())
    assert sha(SOURCE/'link/src/obj-nes-100/firmware.stm')==expected['cases']['warm1']['pressure_seal']['sha256']
    link=work(mode)/'link'
    shutil.copytree(SOURCE/'link',link)
    path=link/'src/nes_plan_service200.c'
    s=path.read_text()
    a=s.index(' /* Supply the first confirmed compact OBJ')
    b=s.index(' if(q->kind==0)',a)
    s=s[:a]+s[b:]
    if mode in ('zero_fit','cut','half_page'):
        from pack_nes_report948 import compact
        compact(link/'src')
    if mode in ('zero','group','zero_fit','cut','half_page'):
        cond='!p->sent && (p->pressure&2) && p->bank_history==2 && p->count==1 && q->kind==1 && q->mask!=255'
    elif mode=='run':
        # 0x82 zero followed by fixed 8-byte compact records. The tail is
        # sorted, so ascending adjacent slots stay together until a gap.
        cond=('!p->sent && (p->pressure&2) && p->obj_start==3 && p->count>1 && '
              'p->buffer[4]==0x82 && q->kind==1 && p->buffer[4+p->bytes-5]+1!=q->slot')
    else:
        raise ValueError(f'unsupported ARM build: {mode}')
    if mode=='half_page':
        # Only lead with zero if the first OBJ fits one four-row half.
        cond=cond.replace('q->mask!=255','(!(q->mask&15) || !(q->mask&240))')
    insertion=' if('+cond+' && !flush(p))return false;\n'
    if mode=='group':
        # The early zero occupies its own E9. Preserve the original first
        # batch width (zero plus 14 compact OBJ records) in the next E9.
        insertion+=' if(p->sent==1 && p->count==14 && p->bytes==14*8 && !p->obj_start && !flush(p))return false;\n'
    s=once(s,' if(!append(p,q))return false;',insertion+' if(!append(p,q))return false;')
    if mode=='cut':
        # Only a mask-triggered zero lead needs its original fourteen slots.
        # The per-generation latch is cleared at the validated EA boundary.
        s=once(s,insertion, ' if('+cond+'){if(!flush(p))return false;p->pressure|=128;}\n')
        s=once(s,'p->pressure<<=1;', 'p->pressure=(p->pressure&1)<<1;')
        s=once(s,' if(!append(p,q))return false;', ' if(!append(p,q))return false;\n if((p->pressure&128) && p->sent==1 && !p->obj_start && p->count==14)return flush(p);')
    path.write_text(s,newline='\n')


def trace(temp,mode,phase):
    import nes_chain935 as chain
    class TraceRows(chain.QueuedPages):
        def __init__(self,args):
            super().__init__(args)
            self.demand948=[]

        def next_rom(self,now):
            kind,address=self.pending[0]
            count=len(self.grants)
            end=super().next_rom(now)
            if self.generation in (909,910) and kind==1:
                issued=self.grants[count:]
                assert len(issued)<=1
                self.demand948.append((self.generation,self.decoded_slot,address,now,end,issued))
            return end

        def exchange(self,seq,t,op,args):
            answer=super().exchange(seq,t,op,args)
            if op=='FINISH':
                (self.a.out/'demand948.json').write_text(json.dumps(self.demand948))
            return answer

    arm=work(mode)
    if mode=='old':
        arm=chain.fit_arm()
    elif mode=='split':
        arm=SOURCE
    rom=chain.output('bounded') if mode=='old' else ROM
    with patch.object(chain,'QueuedPages',TraceRows),patch.object(chain,'output',lambda _:rom):
        chain.replay(temp,'final',phase,'cold','bounded',work_arm=arm,tag='948bound'+mode if mode=='old' else '948trace'+mode)


def replay(temp,mode,phase,cache):
    with patch.object(base.prev.chain,'output',lambda _:ROM):
        base.prev.chain.replay(temp,'final',phase,cache,'bounded',work_arm=work(mode),tag='948'+mode)


def guards(temp,mode):
    import nes_return920
    from check_nes_supply905_arm import run as proof
    from nes_order938 import empty_next_offer
    arm=work(mode)
    proof(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',arm,925,
          short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    with patch.object(nes_return920,'client',lambda _:ROM):
        nes_return920.guards(temp,'first',tag='948'+mode,destination=arm/'final-guards.json')
    prior.check_obj_recovery(temp,mode,work=work,prefix='948')
    if mode in ('zero_fit','cut','half_page'):
        verify_report(mode)


def verify_report(mode):
    from pack_nes_report948 import check_link
    arm=work(mode)
    result=dict(firmware=sha(arm/'link/src/obj-nes-100/firmware.stm'),
                words=check_link(arm/'link/src',SOURCE/'link/src'))
    (arm/'report948.json').write_text(json.dumps(result)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','trace','guards'))
    parser.add_argument('mode',choices=MODES+('old','split'))
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',type=int,nargs='?',choices=(1,2))
    parser.add_argument('cache',nargs='?',choices=('warm','cold'))
    args=parser.parse_args()
    if args.mode not in MODES and args.action!='trace':
        parser.error('old and split are passive trace controls')
    if args.action in ('trace','replay') and args.phase is None:
        parser.error('a replay phase is required')
    if args.action=='replay' and args.cache is None:
        parser.error('a replay cache is required')
    if args.action=='prepare':
        prepare(args.mode)
    elif args.action=='guards':
        guards(args.temp,args.mode)
    elif args.action=='trace':
        trace(args.temp,args.mode,args.phase)
    else:
        replay(args.temp,args.mode,args.phase,args.cache)
