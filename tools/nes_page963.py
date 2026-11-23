"""Build and replay a source-derived, generation-qualified cache hint on the ARM."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_chr951
from nes_companion952 import complete_row_set, replay, supply
from nes_blank960 import WORK, PACKED
from nes_tail961 import next_pair
from nes_raw506 import once
from test_nes_banks557 import crc
from nes_ready958 import directory
from replay_nes_supply905 import joint

ARM=WORK.parent/'nes-page963'
HERE=Path(__file__).resolve().parent
C_CODE=HERE/'nes_page963.c'


def prepare():
    link=ARM/'link'
    shutil.copytree(WORK/'link',link)
    src=link/'src'
    f=src/'nes_native_runtime165.c'
    body=f.read_text()
    start='static bool planner221(struct nes_native_runtime165 *s){'
    body=once(body,start,C_CODE.read_text()+'\n'+start)
    f.write_text(once(body,' bool ok=nes_native_video211_plan(',''' if(s->plan.bank_history==2 && !page_hint963(s))return false;
 bool ok=nes_native_video211_plan('''),newline='\n')


def page_reader(parent,enabled,neighbor):
    class Pages(parent):
        page=None

        def accept(self,tx,t):
            if tx[0]!=0xeb:
                return super().accept(tx,t)
            gen=int.from_bytes(tx[1:3],'little')
            base=int.from_bytes(tx[3:5],'little')
            assert len(tx)==7 and gen==self.generation and base<8192 and base%8==0
            assert crc(tx[:5],8,7,0)==tx[5] and tx[6]==0xa5 and not self.stopped
            self.begin()
            if not hasattr(self,'hint_log'):
                self.hint_log=[]
                self.fills=[]
            self.hint_log.append([gen,base,round(t),tx.hex()])
            if enabled and not self.cache[str(gen)]:
                self.page=(gen,base,0,t)
            return t

        def cancel_supply(self):
            self.page=None
            super().cancel_supply()

        def pump(self,now):
            if self.page and not self.stopped:
                g,base,row,opened=self.page
                self.begin()
                if self.owner!=g:
                    self.page=None
                else:
                    # The hint can borrow the pre-plan interval only. E9/demand
                    # and STOP own the port whenever a normal request appears.
                    batches=self.phases.get(g,{}).get('banks557',[])
                    end=min(now,batches[0]['seal']) if batches else now
                    limit=128 if neighbor else 64
                    while row<limit:
                        tile=(base if row<64 else base^8)+(row%64)//8
                        addr=tile*16+row%8
                        at=max(self.free,opened)+2
                        if at>=end:
                            break
                        if addr in self.store and self.store[addr][0]<=at:
                            opened=at
                        else:
                            grant,reply=self.original_select(at)
                            if grant>=end:
                                break
                            self.free=opened=reply+1
                            self.store[addr]=(reply,self.chr[addr],self.chr[addr+8])
                            self.fills.append((g,addr,grant,reply))
                        row+=1
                    self.page=(g,base,row,opened) if row<limit and not batches else None
            return super().pump(now)

        def exchange(self,seq,t,op,args):
            ret=super().exchange(seq,t,op,args)
            if op=='FINISH':
                grants=[v[3] for v in self.grants]+[v[2] for v in self.spec+self.ahead_log+getattr(self,'fills',[])]
                assert len(grants)==len(set(grants))
                (self.a.out/'hint963.json').write_text(json.dumps(dict(hints=getattr(self,'hint_log',[]),
                                                                      fills=getattr(self,'fills',[]))))
            return ret
    return Pages


def simulate(temp,phase,cache,enabled,work,neighbor,*,feedback=None,tag=None):
    init=joint.Runtime.__init__
    def charge(cpu,*args):
        init(cpu,*args)
        # Same seven-byte callback and status accounting as EA.
        controls=json.loads((directory(temp,phase,'961wirepair','cold')/'events.json').read_text())
        ea=next(e for e in controls if e.get('opcode')=='0xea' and e['bytes']==7)
        cpu.driver_extra[0xeb]=ea['clock']-ea['start']-7*8*joint.MASTER/2625000
    with patch.object(joint.Runtime,'__init__',charge),patch.object(nes_chr951,'ROM',PACKED),complete_row_set():
        def wrap(base):
            reader=page_reader(supply(base,'checked',redirect=next_pair),enabled,neighbor)
            return feedback(reader) if feedback else reader
        replay(temp,phase,cache,'banked',wrap=wrap,
               tag=tag or '963b'+work.name+('both' if neighbor else 'on' if enabled else 'off'),work_arm=work,edition=955)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','replay'])
    p.add_argument('--phase',type=int,choices=(1,2))
    p.add_argument('--temp',type=Path)
    p.add_argument('--cache',choices=('cold','warm'),default='cold')
    p.add_argument('--enabled',action='store_true')
    p.add_argument('--neighbor',action='store_true')
    p.add_argument('--work',type=Path,default=ARM)
    a=p.parse_args()
    if a.action=='prepare':
        prepare()
    else:
        simulate(a.temp,a.phase,a.cache,a.enabled or a.neighbor,a.work,a.neighbor)
