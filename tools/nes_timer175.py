# SPDX-License-Identifier: MIT
"""Remove an already established timed-phase test from the counter guard.

phase_step has one consumer, the else branch after !timed_phase. Its value
outside timed phases is unobservable. Fault/STOP/write-drain priorities stay
identical. This targets the measured load_begin -> phase_step -> remaining ena
path in ready175, not a placement seed or clock change.
"""
from pathlib import Path
import argparse,json
from nes_game147 import sha
from nes_ready175 import prepare as ready_prepare,transform as ready

def transform(s):
    s=ready(s)
    old='     (timed_phase && !(accepted_load_begin || accepted_load_end || accepted_start || stop));'
    assert s.count(old)==1 and s.count('phase_step')==2
    assert 'else if(!timed_phase)' in s and 'else if(phase_step)' in s
    return s.replace(old,'''     !(accepted_load_begin || accepted_load_end || accepted_start || stop);
 //175 phase_step is consumed only after !timed_phase was excluded below.''')

def prepare(prior,out):
    r=ready_prepare(prior,out);n='nes_rom_loader.sv'
    (out/n).write_text(transform((prior/n).read_text()),encoding='utf8',newline='\n')
    r['sources'][n]=sha(out/n);r['public_sources']['tools/nes_timer175.py']=sha(Path(__file__))
    r['timer_contract']='phase_step only consumed in timed phases; reset, hold and fault drain unchanged'
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
