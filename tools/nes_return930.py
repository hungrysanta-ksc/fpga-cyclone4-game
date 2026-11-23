"""Try a checked producer handoff after the OBJ idle-DMA opportunity, before OAM fill."""
import argparse
import json
import shutil
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once
import nes_window924
from nes_window924 import replay
from prepare_nes_trial925 import WORK as ORIGINAL


def image(mode):
    return ORIGINAL if mode in ('base','supply') else ORIGINAL.parent/f'nes-return930-{mode}'


class SupplyTrace(nes_window924.LeadingRecord):
    """Bind each actual row lookup and normal grant to the decoded OBJ slot."""
    def __init__(self,args):
        super().__init__(args)
        self.row_log=[]

    def decode557(self,q,arrived,now):
        at=super().decode557(q,arrived,now)
        if at<=now:
            self.decoded_slot=int.from_bytes(q[2:4],'little')
        return at

    def next_rom(self,t):
        kind,addr=self.pending[0]
        count=len(self.grants)
        end=super().next_rom(t)
        if self.generation==912 and kind==1:
            grants=self.grants[count:]
            assert len(grants)<=1
            self.row_log.append([32*self.decoded_slot,addr,t,end,grants])
        return end

    def exchange(self,seq,t,op,args):
        lines=super().exchange(seq,t,op,args)
        if op=='FINISH':
            (self.a.out/'slots930.json').write_text(json.dumps(self.row_log)+'\n')
        return lines


def prepare(mode):
    if mode in ('base','supply'):
        raise ValueError('use the original MMC925 image for the control')
    link=image(mode)/'link'
    shutil.copytree(ORIGINAL/'link',link)
    path=link/'src/nes_native_sink165.c'
    limit=12 if mode=='handoff' else 1
    old='    !wait_map880(s->plan->window,12))return fail(s,5);'
    new=f'''    (!wait_map880(s->plan->window,{limit}) ||
     (!(s->plan->window->status_flags&8) &&
      !nes_plan200_progress(s->plan,NES_ORDINARY553))))return fail(s,5);'''
    # A confirmed DMA ends the wait as before. Otherwise service the producer
    # once through the normal CRC, ownership and STOP checks before the OAM
    # fill can take the consumer. Never poll inside a partial SPI transaction.
    if mode=='prefix':
        # The first literal OAM head can otherwise strand the next OBJ behind
        # a large checked bulk. Keep the original idle window before OAM fill.
        old=' /* Let an already submitted OBJ return before issuing the OAM fill.'
        new=''' if(op==2 && section==4 && at==0 && s->plan && s->plan->bulk_pending &&
    s->plan->bulk[1] && s->plan->bulk[3] &&
    !nes_plan200_progress(s->plan,NES_ORDINARY553))return fail(s,5);
'''+old
    path.write_text(once(path.read_text(),old,new), newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay'))
    p.add_argument('mode',choices=('base','supply','handoff','short','prefix'))
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    p.add_argument('--cold',action='store_true')
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    else:
        observer=patch.object(nes_window924,'LeadingRecord',SupplyTrace) if a.mode=='supply' else nullcontext()
        with observer:
            replay(a.temp,'objheader',a.phase,a.cold,arm=image(a.mode),edition=925,
                   tag='930'+a.mode,trace_last=True)
