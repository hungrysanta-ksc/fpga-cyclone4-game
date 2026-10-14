# SPDX-License-Identifier: MIT
"""A5 snapshot plus reachable-state removal of redundant READY release gating.

Only load_ready drops release_reset[1]; external reset remains an immediate
clamp. Phase is asynchronously IDLE on reset and remains IDLE for every edge
with active_reset. RECEIVE therefore implies release_reset==0 after reset.
No command/snapshot edge, write drain, reset synchronizer or clock changes.
"""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_snapshot175 import prepare as snapshot

def transform(s):
    old=' assign load_ready=!active_reset && !fault && phase[RECEIVE] && loaded_bytes<total;'
    assert s.count(old)==1
    return s.replace(old,''' //175 RECEIVE cannot be set while release_reset is active: phase is
 // asynchronously IDLE and held IDLE through the complete release sequence.
 // Retain the external reset clamp; do not change command eligibility timing.
 assign load_ready=!reset && !fault && phase[RECEIVE] && loaded_bytes<total;''')

def prepare(prior,out):
    r=snapshot(prior,out)
    n='nes_rom_loader.sv'
    (out/n).write_text(transform((prior/n).read_text()),encoding='utf-8',newline='\n')
    r['changed']=[*r['changed'],n];r['sources'][n]=sha(out/n)
    r['public_sources']['tools/nes_ready175.py']=sha(Path(__file__))
    r['ready_contract']='After reset: RECEIVE implies release_reset=0; external reset clamp retained. No extra cycle.'
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
