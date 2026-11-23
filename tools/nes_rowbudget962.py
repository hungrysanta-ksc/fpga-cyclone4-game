"""Cache-state sensitivity; prospective source data is never an accepted plan."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_tail961
from fixture_nes_port914 import fixture
from nes_companion952 import Rows952
from nes_ready958 import directory
from test_nes_service509_schedule import Calendar

TAGS={'one':(3074,), 'four':(3074,3075,3078,3079), 'page':tuple(range(3072,3080))}


def trial(temp,phase,case,wire=False):
    base=directory(temp,phase,'961wirepair','cold')
    calendar=Calendar(temp/'nes-service509-rom03')
    events=json.loads((base/'events.json').read_text())
    now=round(next(e['clock'] for e in events if e['event']=='planner_enter' and e['generation']==909))
    pairs=[]
    for tag in TAGS[case]:
        for row in range(8):
            grant,reply=calendar.select(now)
            pairs.append((tag,row,grant,reply))
            now=reply+3
    # Assume a separate reader knew the targets by planner entry. Preserve
    # existing cache collisions, bank ownership, E9 packets and DMA commands.
    original=nes_tail961.supply
    def preload(*args,**kwargs):
        class Preloaded(original(*args,**kwargs)):
            installed=False
            def pump(self,now):
                if not self.installed and self.generation==909 and now>=pairs[-1][3]:
                    self.begin()
                    assert not self.stopped and self.owner==909
                    for tag,row,_,reply in pairs:
                        a=tag*16+row
                        self.store[a]=reply,self.chr[a],self.chr[a+8]
                    self.installed=True
                return super().pump(now)
            def exchange(self,seq,t,op,args):
                ret=super().exchange(seq,t,op,args)
                if op=='FINISH':
                    occupied={v[3] for v in self.grants}|{v[2] for v in self.spec+self.ahead_log}
                    assert self.installed and occupied.isdisjoint({g for _,_,g,_ in pairs})
                return ret
        return Preloaded
    label='962'+case
    initial=directory(temp,phase,label,'cold')
    evidence=nes_tail961.evidence
    def observed(folder,gen,**kwargs):
        return evidence(initial if gen==909 and wire else folder,gen,**kwargs)
    if wire:
        label+='wire'
    with patch.object(nes_tail961,'supply',preload),patch.object(nes_tail961,'evidence',observed):
        nes_tail961.run(temp,phase,'cold',correction='961pair',output_tag=label,
                        feedback_generations=(908,909) if wire else (908,))
    dest=directory(temp,phase,label,'cold')
    fixture(temp,phase,True,909,label,include_bg=True)
    f=dest/'gen909'
    assert pairs[-1][3]<int((f/'origin914.txt').read_text())
    words=[int(s,16) for s in (base/'gen908/rows-out951.hex').read_text().splitlines() if not s.startswith('//')]
    chr_data=bytes.fromhex((f/'chr914.hex').read_text())
    assert len(words)==256
    displaced=[]
    for tag,row,grant,reply in pairs:
        a=tag*16+row
        bank,lane=Rows952().index(a)
        i=bank*8+lane
        displaced.append(words[i])
        words[i]=(1<<25)|((tag>>4)<<16)|(chr_data[a+8]<<8)|chr_data[a]
    (f/'budget962.hex').write_text(''.join(f'{v:07x}\n' for v in words))
    (f/'budget962.json').write_text(json.dumps(dict(slots=pairs,previous_words=displaced)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('case',choices=TAGS)
    p.add_argument('--wire',action='store_true')
    a=p.parse_args()
    trial(a.temp,a.phase,a.case,a.wire)
