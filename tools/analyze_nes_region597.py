"""Join the 595/596 references, pin-level results and isolated 597 MAPs."""
import argparse
import json
import re
import tempfile
from pathlib import Path

from budget_nes_region597 import ROOT, RTL, build, sha


def read(path):
    return json.loads(path.read_bytes())


def sources_hash(name):
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        build(name)(d)
        return {f:sha(d/f) for f in RTL}


def production(log):
    events = {905:[],906:[]}
    seen_warm = False
    for generation, phase, length, ticks in re.findall(r'PAGE597 (\d+) (\d+) (\d+) (\d+)', log.read_text()):
        g = int(generation)
        if seen_warm and g == 905:
            break  # Subsequent 905 is the injected-CRC trial, with separate accounting.
        seen_warm |= g == 906
        events[g].append(dict(phase=int(phase), page_B=int(length), source_ticks=int(ticks)))
    return events


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('sim',type=Path)
    p.add_argument('map_parts',type=Path)
    p.add_argument('map_combined',type=Path)
    p.add_argument('map_free',type=Path)
    p.add_argument('poll',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    prior=read(ROOT/'analysis/region595-verification.json')
    budget=read(ROOT/'analysis/pages596-verification.json')
    runs={k:read(a.sim/k/'result.json') for k in ('packed','control')}
    polls={k:read(a.poll/k/'result.json') for k in runs}
    for name,run in runs.items():
        assert run['ELF']==prior['ELF'] and run['RTL']==sources_hash(name)
        assert all(polls[name][key]==run[key] for key in ('frames','RTL','ELF'))
    assert runs['control']['frames']==prior['frames']
    guarded=runs['packed']
    assert guarded['repair_rows']==29 and guarded['repair']['actions']==[0,3,4]
    assert guarded['cold_recovery']=={k:v for k,v in guarded['frames'][0].items() if k!='generation'}
    assert guarded['display']==prior['display']
    events={k:production(a.sim/k/'vsim.log') for k in runs}
    rows=[]
    for i,(old,new) in enumerate(zip(runs['control']['frames'],guarded['frames'])):
        g=old['generation']
        assert g==new['generation'] and old['actions']==new['actions']
        pages=old['packets']-new['packets']
        calls=old['calls']-new['calls']
        other=calls-3*pages
        wire=old['wire_B']-new['wire_B']
        assert wire==21*pages+8*other and pages==26
        counts={k:v['polls'][i] for k,v in polls.items()}
        for k,frame in [('control',old),('packed',new)]:
            c=counts[k]
            assert c['pop_confirm']==frame['packets'] and c['request_confirm']==len(frame['actions'])
            assert sum(c.values())+2*frame['packets']+len(frame['actions'])+1==frame['calls']
        assert sum(counts['control'][k]-counts['packed'][k] for k in ('ready','empty'))==other
        detail={}
        for name,expected in [('control',32),('packed',6)]:
            obs=events[name][g]
            assert len(obs)==expected and obs[0]['phase']==2 and obs[-1]['phase']==3
            detail[name]=dict(first_meta_ticks=obs[0]['source_ticks'],first_raw_ticks=next(r['source_ticks'] for r in obs if r['phase']==3),
                              sum_ticks=sum(r['source_ticks'] for r in obs),max_ticks=max(r['source_ticks'] for r in obs),pages=obs)
        rows.append(dict(generation=g,control=old,packed=new,wire_B_saved=wire,calls_saved=calls,
                         other_D0_saved=other,status_counts=counts,wire_only_ms_saved=wire*8/2625,production=detail))
    costs={}
    labels={'LE':'Total logic elements','comb':'Total combinational functions',
            'FF':'Dedicated logic registers','bits':'Total memory bits','pins':'Total pins'}
    for name,parent in [('value_header',a.map_parts),('response',a.map_parts),('packed',a.map_combined),
                        ('joint_core',a.map_combined),('joint',a.map_combined),('free',a.map_free)]:
        summary=(parent/name/'region.map.summary').read_text()
        assert 'Successful' in summary and 'Lite Edition' in summary
        costs[name]={k:int(re.search(r'^\s*'+label+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',','')) for k,label in labels.items()}
        costs[name].update(RTL=sources_hash(name), report=sha(parent/name/'region.map.rpt'))
    result=dict(stage=597,ELF=guarded['ELF'],rows=rows,guards={k:guarded[k] for k in ('repair','repair_rows','partial_D1_token','cold_recovery','display')},
                costs=costs,screen_LE=prior['local_screen_LE'],previous_joint_LE=budget['diagnostics']['joint']['LE'],
                remaining_joint_LE=costs['joint']['LE']-prior['local_screen_LE'],remaining_free_LE=costs['free']['LE']-prior['local_screen_LE'],
                production_period_ns=45.454,scope='Packed producer on original 595 CDC/pin RTL. 594 ARM; fixture collector and display peer. Joint MAP uses diagnostic CDC; free producers are external oracles.')
    a.output.write_bytes((json.dumps(result,indent=2)+'\n').encode())


if __name__=='__main__':
    main()
