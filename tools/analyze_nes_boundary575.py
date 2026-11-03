# SPDX-License-Identifier: MIT
"""Audit scope and preservation checks; raw timing remains the acceptance record."""
import argparse,collections,json,re
from pathlib import Path
from nes_raw506 import sha
from nes_boundary575 import rows,classify

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--traces',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    previous=json.loads((root/'analysis/serial574-verification.json').read_text())
    physical=json.loads((root/'analysis/trial558-verification.json').read_text())['inputs']
    expected_sources=previous['sources'].copy()
    # Source identity is independently pinned by the 573 first-capture evidence.
    old_epoch=json.loads((root/'analysis/epoch573-verification.json').read_text())['boards']['572']['RTL']
    expected_sources['nes_source_epoch207.sv']=old_epoch
    outputs={}
    for name,dirname in [('MMC558','nes-admit556-board01'),('572','nes-start572-loader')]:
        d=a.traces/dirname;old=previous['boards'][name]
        assert sha(d/'output_files/board.sof')==old['SOF']
        assert sha(d/'output_files/board.sta.summary')==old['STA']
        for f,h in (expected_sources if name=='572' else physical).items():assert sha(d/f)==h,f
        raw=rows(d/'boundary575-negative.tsv')
        counts=collections.Counter();groups=collections.defaultdict(list)
        for r in raw:
            k=classify(r);counts[k]+=1
            if r['check']=='setup':assert r['from_clock']!=r['to_clock']
            pair=tuple(re.sub(r'\[\d+\]','[*]',r[c]) for c in ('from','to'))
            groups[(r['check'],k,*pair)].append(r)
        topo=rows(d/'boundary575-topology.tsv')
        fan=collections.defaultdict(list)
        for r in topo:fan[r['first']].append(r)
        for f,rs in fan.items():assert len(rs)==1 and rs[0]['fanout']==rs[0]['expected_second'],f
        chain=rows(d/'boundary575-chains.tsv')
        assert len(chain)==len(fan)*6 and all(float(r['slack'])>0 for r in chain)
        held=rows(d/'boundary575-held-budget.tsv')
        assert len(held)==counts['held_mailbox']+counts['held_rom_address']
        assert all(float(r['slack'])>0 for r in held)
        report=[]
        for (check,k,s,t),rs in sorted(groups.items()):
            report.append(dict(check=check,kind=k,source_family=s,target_family=t,rows=len(rs),
                worst_ns=min(float(r['slack']) for r in rs),
                pairs=sorted({(r['from'].split('|')[-1],r['to'].split('|')[-1]) for r in rs})))
        outputs[name]=dict(counts=dict(counts),negative_rows=len(raw),groups=report,chains=len(fan),
            chain_min_ns={k:{c:min(float(r['slack']) for r in chain if r['class']==k and r['check']==c) for c in ('setup','hold')} for k in {r['class'] for r in chain}},
            held_budget_min_ns={k:min(float(r['slack']) for r in held if r['class']==k) for k in ('held_mailbox','held_rom_address')},
            raw_SOF=old['SOF'],raw_STA=old['STA'],raw_fit=old['fit'],raw_worst=old['worst'],
            reports={n:sha(d/n) for n in ('boundary575-negative.tsv','boundary575-counts.tsv','boundary575-clocks.rpt','boundary575-transfers.rpt','boundary575-topology.tsv','boundary575-chains.tsv','boundary575-held-budget.tsv')},
            constraints={n:sha(d/n) for n in ('board.qsf','board.sdc','nominal204.sdc','cdc181.sdc')})
    assert outputs['572']['negative_rows']==545 and outputs['572']['counts'].get('legacy_raw_control',0)==0
    tests=json.loads((a.traces/'nes-boundary575-test03/result.json').read_text())
    for f,h in tests['RTL'].items():assert sha(a.traces/'nes-start572-loader'/f)==h
    tests['logs']={p.name:sha(p) for p in (a.traces/'nes-boundary575-test03').glob('*.log')}
    evidence=dict(boards=outputs,tests=tests,selected='572 START only',new_FIT=False,board_constraints_changed=False,new_physical_run=False,
        preserved_schedule_reference='analysis/start572-verification.json',
        next=['Exact CDC scope with physical settling and held-data bounds, compare both boards under the same proposed constraints; preserve raw STA.',
              'Review raw diagnostic bus_drive snapshot and guarded reset samplers before exceptions.',
              'Retain immediate STOP/fault cancellation and verify first capture/cache/plan and continuous display before any release.'],
        scope='Worst negative path per destination per clock pair, across three corners; not all combinational paths or unconstrained IO. Held-data budget is a temporary STA measurement of listed paths, not a new accepted board constraint or physical signoff.')
    a.out.write_text(json.dumps(evidence,indent=2)+'\n',newline='\n')

if __name__=='__main__':main()
