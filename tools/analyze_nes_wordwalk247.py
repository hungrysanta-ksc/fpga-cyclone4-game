# SPDX-License-Identifier: MIT
"""Reuse the independent actual-command oracle; measure new word traversal.

Only diagnostic-specific assertions change; old scan evidence is immutable.
"""
from pathlib import Path
import argparse,csv,inspect,json
import analyze_nes_scan247 as reference
from nes_delta231 import once,sha


def analyze(build,test,prior,observer,model,previous):
    source=inspect.getsource(reference.analyze)
    for before,after in (
        ("b['body_bytes']==3930","b['body_bytes']==3920"),
        ("end['service_visits']==192","end['service_visits']==96"),
        ('service_visits=192','service_visits=96'),
        ("warm=rows[2:];assert all(r['scan_ms']>1000/60 for r in warm)","warm=rows[2:]"),
        ("decision='REJECT_per_bit_full_scan_latency'","decision='FUNCTIONAL_diagnostic_only_joint_gate_open'"),
        ('body_bytes=3930,body_free=6','body_bytes=3920,body_free=16'),
        ('scanner_bytes=283','scanner_bytes=273'),
        ('warm_scan_over_16_67_ms=len(warm)',"warm_scan_over_16_67_ms=sum(r['scan_ms']>1000/60 for r in warm)"),
        ('Observed scanner latency already exceeds frame period; no need to pretend observed max is WCET.','Observed latency is not WCET or whole-path latency.'),
        ('192 service entry intervals','96 service entry intervals'),
    ):source=once(source,before,after)
    ns=dict(reference.__dict__);ns['__file__']=__file__
    exec(compile(source,'wordwalk247-oracle','exec'),ns)
    result=ns['analyze'](build,test,prior,observer)
    m=json.loads(model.read_text(encoding='utf-8'));p=json.loads(previous.read_text(encoding='utf-8'))
    assert m['passed'] and p['decision']=='REJECT_per_bit_full_scan_latency'
    for row,old,work in zip(result['rows'],p['rows'],m['rows']):
        assert row['frame']==old['frame']==work['frame']
        assert row['commands']==old['commands']==work['final_commands']
        assert row['dma_bytes']==old['dma_bytes'] and row['charge']==old['charge']
        row.update(previous_scan_master_clocks=old['scan_master_clocks'],
                   removed_scan_master_clocks=old['scan_master_clocks']-row['scan_master_clocks'],
                   modeled_word_shift_steps=work['word_shift_steps'],modeled_set_units=work['units'])
    for path in (model,previous,Path(reference.__file__)):
        result['input_hashes'][path.relative_to(reference.BASE).as_posix()]=sha(path)
    result.update(structural_change='96 word loads;zero word skip;shift nonzero tail;address/run work only on set bits',
                  old_command_lists_unchanged=True,remaining_wholepath_gate='Source/wire/ARM/scan/upload/final ownership and deadlines remain unbound.',
                  cold_scan_ms=[r['scan_ms'] for r in result['rows'][:2]],
                  code_comparison=dict(original232=3910,full_scan_rejected=3930,word_walk=3920,limit=3936))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','test','prior','observer','model','previous','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    r=analyze(*(getattr(a,k).resolve() for k in ('build','test','prior','observer','model','previous')))
    raw=a.out/'result.json';raw.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in r.items() if k not in ('rows','input_hashes')}
    public.update(input_count=len(r['input_hashes']),private_result_sha256=sha(raw))
    public['residual_rows']=[v for v in r['rows'] if v['frame'] in (952,954,955,963,968)]
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(r['rows'][0]),lineterminator='\n');w.writeheader();w.writerows(r['rows'])
    print(json.dumps({k:v for k,v in public.items() if k!='residual_rows'},indent=2))


if __name__=='__main__':main()
