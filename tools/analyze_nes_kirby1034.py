"""Separate what the two physical MMC1027 generations and later ingress controls actually recorded."""
import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

from analyze_nes_kirby1033 import measurements, workload
from read_nes_ingress1029 import MS, boundaries, decode
from read_nes_tail1012 import decode as decode_tail


TARGET_WORKLOAD=(661,16,2,15,4,1,192,320)


def physical(main, controls):
    raw=main.read_bytes()
    report=decode_tail(raw,1027)
    stages=[]
    for gen in (1526,1561):
        (i,r),=[(i,r) for i,r in enumerate(report['rows']) if r['generation']==gen]
        if workload(r)!=TARGET_WORKLOAD:
            raise ValueError('unexpected source or workload')
        stages.append(measurements(r,boundaries(raw,i,r,1027)))
    detailed=[s['generation'] for s in report['samples']]
    if set(detailed)&{1526,1561}:
        raise ValueError('recheck packet trace availability')
    a,b=stages
    x,y=(r['previous_show_to_input_complete_ms'] for r in stages)
    result=dict(main_sha256=hashlib.sha256(raw).hexdigest(), packet_detail_generations=detailed,
                stages=stages, input_completion_shift_ms=[y[0]-x[1],y[1]-x[0]],
                first_E9_shift_ms=(b['stage_ticks']['to_first_E9']-a['stage_ticks']['to_first_E9'])*MS,
                last_plan_shift_after_E9_ms=(b['stage_ticks']['to_last_plan']-a['stage_ticks']['to_last_plan'])*MS,
                historical_first_ready_D1_D2=None,historical_individual_E9_and_returns=None,controls=[])
    for ed, path in controls:
        data=path.read_bytes()
        rows=[r for r in decode(data,ed)['rows'] if 'timing' in r]
        pairs=[]
        for r,s in combinations(rows,2):
            def key(t):
                return workload(t)+(t['input']['blocks'],t['input']['payload_bytes'])
            if (not 0<s['tick']-r['tick']<=200 or key(r)!=key(s) or
                    abs(r['spacing_ms']-s['spacing_ms'])<16-2*MS):
                continue
            pair=[]
            for t in (r,s):
                ingress=t['input']
                duration=ingress['first_D1_to_last_return_ms']
                pair.append(dict(gen=t['generation'],seconds=t['tick']/100,work=key(t),
                                 first_D1_from_prev_ms=[x-duration for x in t['timing']['previous_show_to_input_complete_ms']],
                                 D1_to_confirmed_D0_ms=duration, D1_wire_ms=ingress['D1_ms'],
                                 restore_ms=ingress['restore_and_check_ms'],D2_D0_ms=ingress['D2_and_D0_ms'],
                                 between_blocks_ms=ingress['between_blocks_ms'],ready_to_D1_ms=t.get('ready_to_D1_ms'),
                                 show_ms=t['spacing_ms'],ACK_ms=t['timing']['previous_show_to_ACK_ms']))
            pairs.append(pair)
        result['controls'].append(dict(edition=ed,sha256=hashlib.sha256(data).hexdigest(),pairs=pairs,
                                       exact_target_workload=sum(workload(r)==TARGET_WORKLOAD for r in rows)))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',type=Path)
    parser.add_argument('controls_dir',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    report=physical(args.target,[(e,args.controls_dir/f'nes-frame-mmc{e}.bin') for e in range(1029,1033)])
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
