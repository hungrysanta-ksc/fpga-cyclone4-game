"""Compare linked decompression experiments and the 53-frame M4/65816 schedules."""
import argparse
import json
from pathlib import Path
from statistics import median
from collections import Counter

from analyze_nes_phase537 import Calendar, ROOT, csv_groups, ms, one, read, sha
from analyze_nes_seal538 import inspect_run


def budget():
    frames=read(ROOT/'analysis/planner607-comparison.json')['frames']
    old=read(ROOT/'analysis/overlap606-verification.json')['phases']
    result=[]
    for phase in old:
        for row in frames:
            if row['generation']!=954:
                continue
            control=next(r for r in frames if r['generation']==954 and r['variant']=='control')
            # Both prefix timelines use the same six verified POPs. Prefix work must
            # be charged on its actual side of the earlier frame's EA.
            after=row['first_E9_ms']-row['prefix6_ms']
            tail=phase['conditional_SEAL_floor_after_overlap_ms']-phase['first_E9_after_overlap_ms']
            result.append(dict(phase=phase['phase'],variant=row['variant'],
                first_E9_after_six_hidden_ms=after, deadline_ms=phase['deadline_ms'],
                uncompressed_output_wire_SEAL_floor_ms=after+tail,
                ideal_all_input_hidden_batched_compact_with_driver_ms=(
                    phase['ideal_batched_compact_plus_mean_driver_ms']+
                    (row['first_E9_ms']-row['commit_ms'])-(control['first_E9_ms']-control['commit_ms']))))
    return result


def phase(a,i,candidate):
    base=a.traces/f'nes-close561-run{i}'
    run=a.traces/f'{candidate}{i}'
    fixed=read(ROOT/'analysis/whole580-verification.json')['phases'][i-1]
    assert all(sha(base/n)==value for n,value in fixed['evidence'].items())
    fw=a.firmware
    obj=read(run/'obj-phases.json')
    requests={int(g):p['first_BG561'] for g,p in obj.items() if 'first_BG561' in p}
    metrics=inspect_run(run,a.plans,Calendar(a.calendar),base,sha(fw),
                        sha(a.client/'sink165.sfc'),first_bg_limit=3,first_bg_requests=requests,
                        request_log_offsets=getattr(a,'request_log_offsets',None))
    before=read(ROOT/'analysis/close561-verification.json')['phases'][i-1]['early']
    result={}
    for label,path,data in [('control',base,before),('candidate',run,metrics)]:
        events=read(path/'events.json');phases=read(path/'obj-phases.json')
        cpu=csv_groups(path/'window.csv')
        result[label]={k:data[k] for k in ('dense_VB','dense_ms','dense_frames','last_ACK','ROM_reads',
                                            'DMA_B','ARM_instructions','IRQ','SPI_B','pins')}
        result[label]['dense_frames']={int(k):v for k,v in data['dense_frames'].items()}
        displays=[one([e for e in cpu[g] if e['op']==3],'reveal')['clock'] for g in range(905,958)]
        intervals=sorted(ms(b-a) for a,b in zip(displays[1:],displays[2:]))
        result[label]['after_first_two']=dict(intervals=len(intervals),median_ms=median(intervals),
            p95_nearest_rank_ms=intervals[-3],max_ms=max(intervals),mean_ms=sum(intervals)/len(intervals))
        result[label]['watched']={}
        for g in (952,954,957):
            group=[e for e in events if e['generation']==g]
            source=one(group,'source_begin')['clock']
            prev=one([e for e in cpu[g-1] if e['op']==3],'reveal')
            seal=[e for e in cpu[g] if e['op']==3]
            final=one(seal,'final212')['clock']
            first=next(e for e in group if e.get('opcode')=='0xe9')['clock']
            request=phases[str(g)].get('first_BG561')
            grant=Calendar(a.calendar).select(request)[0] if request is not None else None
            reveal=one(seal,'reveal')
            wire=Counter()
            for e in group:
                if e['event']=='SPI':
                    wire[e['opcode']]+=e['bytes']
                elif e['event']=='observer':
                    wire[e['opcode']]+=8
            if label=='control':
                assert dict(wire)==fixed['frames'][str(g)]['operation_wire_B']
            seal_tx=next(e for e in group if e.get('opcode')=='0xe1' and e['packet_opcode']==3)
            result[label]['watched'][g]=dict(E9_after_source_ms=ms(first-source),
                transaction_B=sum(wire.values()),wire_by_op=dict(wire),
                last_payload_after_previous_reveal_ms=ms(seal_tx['clock']-prev['clock']),
                BG_grant_after_source_ms=ms(grant-source) if grant is not None else None,
                BG_wait_ms=ms(grant-request) if grant is not None else None,
                last_OBJ_after_previous_reveal_ms=ms(phases[str(g)]['last_obj_rom_response']-prev['clock']),
                SEAL_load_after_previous_reveal_ms=ms(one(seal,'load')['clock']-prev['clock']),
                interval_VB=reveal['frame']-prev['frame'], interval_ms=ms(reveal['clock']-prev['clock']),
                final_waits=sum(e['event']=='wait169' and e['clock']>=final for e in seal))
    return dict(phase=i,**result,last_ACK_gain_ms=ms(before['last_ACK']-metrics['last_ACK']),
                dense_mean_gain_ms=before['dense_ms']-metrics['dense_ms'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','plans','calendar','client','firmware','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--run-prefix',required=True)
    a=p.parse_args()
    report=dict(stage=607,firmware_B=a.firmware.stat().st_size,firmware_SHA256=sha(a.firmware),
                prefix_sensitivities=budget(),phases=[phase(a,i,a.run_prefix) for i in (1,2)],
                scope='CPI2 linked ARM, real SysTick and 65816, periodic recorded ROM grants, measured average SPI driver; physical FPS unmeasured.')
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
