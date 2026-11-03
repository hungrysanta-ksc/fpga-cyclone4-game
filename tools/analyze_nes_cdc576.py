# SPDX-License-Identifier: MIT
"""Reconcile the single routed 576 candidate, exact CDC checks and fixed display replay."""
import argparse,json
from collections import Counter
from pathlib import Path
from nes_raw506 import sha
from nes_cdc576 import rows,classify
from analyze_nes_owner562 import board
from analyze_nes_reuse565 import pin_budget

p=argparse.ArgumentParser();p.add_argument('--traces',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();t=a.traces;root=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
previous=read(root/'analysis/boundary575-verification.json')
candidate=t/'nes-cdc576-board01';reference=t/'nes-start572-loader'
names=[p.name for p in reference.iterdir() if p.suffix in ('.sv','.v')]
changed=sorted(n for n in names if sha(reference/n)!=sha(candidate/n))
assert changed==['fxpak_nes_screen137_top.sv','nes_screen_status151.sv','nes_sink_bridge165.sv']
results={}
for name,dirname,key in [('MMC558','nes-admit556-board01','558'),('572','nes-start572-loader','572'),('576','nes-cdc576-board01','576')]:
    d=t/dirname;new=name=='576'
    raw=rows(d/('raw576-negative.tsv' if new else 'boundary575-negative.tsv'))
    normalized=rows(d/('boundary575-negative.tsv' if new else 'cdc576-negative.tsv'))
    spec=read(root.parent/f'probes/nes-cdc576/{key}-selected/manifest.json')
    assert sha(d/'cdc576.sdc')==spec['constraints']
    bounded=rows(d/'cdc576-bounded.tsv');settling=rows(d/'cdc576-settling.tsv')
    assert len(bounded)==3*len(spec['pairs'])
    assert all(float(r['slack'])>=0 for r in bounded+settling)
    assert len(settling)%6==0
    gray=[r for r in bounded if r['kind']=='gray_first']
    assert len(gray)==96 and all(float(r['budget'])==5.952 for r in gray)
    if not new:
        assert sha(d/'output_files/board.sof')==previous['boards'][name]['raw_SOF']
        assert sha(d/'output_files/board.sta.summary')==previous['boards'][name]['raw_STA']
    result=dict(raw_counts=dict(Counter(classify(r) for r in raw)),
        raw_negative_rows=len(raw),raw_worst={k:min([float(r['slack']) for r in raw if r['check']==k],default=None) for k in ('setup','hold','recovery','removal')},
        normalized_negative_rows=len(normalized),normalized_counts=dict(Counter(classify(r) for r in normalized)),
        normalized_negative_worst={k:min([float(r['slack']) for r in normalized if r['check']==k],default=None) for k in ('setup','hold','recovery','removal')},
        first_to_second_chains=len(settling)//6,
        settling_min_ns={k:min(float(r['slack']) for r in settling if r['check']==k) for k in ('setup','hold')},
        finite_pairs=len(spec['pairs']),bounded_min_ns={k:min(float(r['slack']) for r in bounded if r['kind']==k) for k in sorted({r['kind'] for r in bounded})},
        reset_pins=len(spec['reset_registers']),
        spec=spec,SOF=sha(d/'output_files/board.sof'))
    if new:
        result['board']=board(d);result['conditional_psram']=pin_budget(d)
        assert normalized==[]
        assert min(result['board']['worst'].values())>=0
        assert result['conditional_psram']['worst_ns']>0
    results[name]=result
assert results['MMC558']['normalized_negative_rows']==471 and results['572']['normalized_negative_rows']==24
tests={}
for kind,dirname in [('diagnostic_reset','nes-cdc576-test05'),('bus','nes-cdc576-bus01'),('start_slots','nes-cdc576-start01')]:
    d=t/dirname;tests[kind]=read(d/'result.json')
    tests[kind]['logs']={p.name:sha(p) for p in d.glob('*.log')}
for n,h in tests['diagnostic_reset']['sources'].items():
    assert sha((t/'nes-cdc576-test05' if n=='reference.sv' else candidate)/n)==h
assert tests['diagnostic_reset']['top']==sha(candidate/'fxpak_nes_screen137_top.sv')
assert tests['bus']['top']==sha(candidate/'fxpak_nes_screen137_top.sv')
schedule=read(root/'analysis/start572-verification.json')['schedule']
for phase in (1,2):
    d=t/f'nes-cdc576-replay{phase}';old=t/f'nes-epoch573-replay{phase}'
    assert read(d/'result.json')['passed'] and read(d/'result.json')['commits']==53
    for n in ('arrivals.tsv','window.csv','bank561.csv'):
        assert sha(d/n)==sha(old/n),n
    assert read(d/'result.json')['frames']==read(old/'result.json')['frames']
    schedule[phase-1]['576_replay']={n:sha(d/n) for n in ('result.json','audit.json','arrivals.tsv','window.csv','bank561.csv')}
out=dict(selected='576 conditional development candidate; MMC558 physical reference unchanged',boards=results,
    changed_RTL=changed,RTL={n:sha(candidate/n) for n in names},tests=tests,schedule=schedule,
    host_admission=dict(reference_edges=3,candidate_edges=5,extra_ns=23.808,steady_packet_change=False),
    original_fitted_extension=sha(candidate/'initial576.sdc'),
    final_routed_extension=sha(candidate/'cdc576.sdc'),
    one_FIT=True,post_route_constraint_rebinding=True,new_hardware=False,new_release=False,
    limitations=['54 input and 57 output ports still have unconstrained IO paths; not whole-board electrical signoff.',
        'Final minimum setup 0.045 ns; prior 572 related setup 0.286 ns. No route-seed tuning.',
        'One FIT used provisional exact names; final route aliases and tighter Gray bound verified by STA only, no second FIT.',
        'Fixed prior ARM/SPI/IRQ/ROM arrivals replayed separately from RTL; no new continuous multi-clock physical FPS or menu run.'],
    next=['Review the 168 MHz load_end to remaining[0] path and external IO coverage before a physical release.',
        'Keep 952/957 final-wait zero and final ACK; do not retry epoch serialization or placement seeds.',
        'Physical trial uses new filenames, no RESTORE, and 5-40s / 40-55s counts.'])
a.out.write_text(json.dumps(out,indent=2)+'\n',newline='\n')
print(json.dumps({k:dict(negative=v['normalized_negative_rows'],chains=v['first_to_second_chains'],bounds=v['bounded_min_ns']) for k,v in results.items()}))
