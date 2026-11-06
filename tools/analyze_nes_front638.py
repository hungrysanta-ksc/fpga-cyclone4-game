# SPDX-License-Identifier: MIT
"""Partition 953 on a single master clock and compare both starts in each boot condition."""
import argparse
import bisect
import json
from pathlib import Path
from analyze_nes_dma637 import trace, csv_groups, one, ms, read, sha, work
from test_nes_service509_schedule import Calendar


def timing(folder, calendar):
    events = read(folder/'events.json')
    rows = csv_groups(folder/'window.csv')
    display = one([r for r in rows[952] if r['op']==3], 'reveal')['clock']
    owner = [r for r in events if r['generation']==953]
    spi = [r for r in events if r.get('input_generation')==953]
    reads = [r for r in spi if r['opcode']=='0xd1']
    commit, = [r for r in spi if r['opcode']=='0xd3']
    assert reads[-2]['clock'] < commit['start'] < reads[-1]['clock']
    pops = [r for r in spi if r['opcode']=='0xd2']
    release = next(r['clock'] for r in events if r['generation']==952 and r.get('opcode')=='0xea')
    assert release < commit['start'] and len(reads)==len(pops)
    planner = one(owner,'planner_enter')['clock']
    packets = [r for r in owner if r.get('opcode')=='0xe9']
    obj = read(folder/'obj-phases.json')['953']
    req,grant,response = next(r[2:5] for r in obj['cache611'] if r[0]==0 and r[-1]=='ROM')
    assert calendar.select(req+1)==(grant,response)
    period,offset=divmod(req+1,calendar.period)
    prev_index=bisect.bisect_left(calendar.starts,offset)-1
    previous=(period-int(prev_index<0))*calendar.period+calendar.starts[prev_index]
    accepted=one([r for r in rows[953] if r['op']==3],'load')['clock']
    push=next(e for e in owner if e.get('packet_opcode')==3)
    stamps=dict(old_EA=release,last_data_D1=reads[-2]['clock'],D3=commit['clock'],
                commit_pop=pops[-1]['clock'],planner=planner,first_E9=packets[0]['clock'],
                first_BG=req,first_grant=grant,first_response=response,last_OBJ=obj['last_obj_rom_response'],
                SEAL_push=push['clock'],SEAL_accept=accepted)
    # Charge only the part after the previous reveal. An in-flight D1 can
    # straddle it. The interval before D2 includes CRC, restore and guard.
    def exposed(start,end):
        return max(0,end-max(display,start))
    assert len(reads)==len(pops) and all(r['clock']<=p['start'] for r,p in zip(reads,pops))
    pre_d3=[(r,p) for r,p in zip(reads,pops) if r['clock']<commit['start']]
    wire=sum(exposed(r['start'],r['clock']) for r,p in pre_d3)
    restore=sum(exposed(r['clock'],p['start']) for r,p in pre_d3)
    return dict(D1_transfer_after_display_ms=ms(wire),D1_return_to_POP_after_display_ms=ms(restore),
                from_display952_ms={k:ms(v-display) for k,v in stamps.items()},
                last_data_to_D3_ms=ms(commit['clock']-reads[-2]['clock']),
                grant_wait_ms=ms(grant-req),previous_grant_missed_ms=ms(req-previous),
                planner_to_first_E9_ms=ms(packets[0]['clock']-planner),
                previous_display_clock=display,previous_grant=previous,first_response=response,
                seal_after_last_OBJ_ms=ms(accepted-obj['last_obj_rom_response']),
                E9_bytes=[e['bytes'] for e in packets], D1_bytes=[e['bytes'] for e in reads],
                pre_display_pops=sum(e['clock']<=display for e in pops))


def analyze(a):
    old = read(Path('analysis/dma637-verification.json'))['two']['phases']
    calendar = Calendar(a.calendar)
    cases = []
    for i,z in enumerate(old):
        phase=z['phase']
        suffix=f"{phase}{'d' if z['boot']=='during' else 'h'}"
        base=a.traces/f'nes-dma637-two{suffix}'
        ref=z['candidate']
        assert all(sha(base/k)==v for k,v in ref['pins'].items())
        base_work=work(base)
        reference_time=timing(base,calendar)
        modes={}
        for mode in ('receive','first','both'):
            folder=a.traces/f'nes-front638-{mode}{suffix}'
            if (folder/'callback-error.txt').exists():
                # Preserve the failed host run. Only a fresh full run is eligible.
                assert 'Maximum execution time' in (folder/'callback-error.txt').read_text()
                folder=folder.with_name(folder.name+'-r2')
            observed=trace(folder,base)
            assert work(folder)==base_work
            assert observed['client']==ref['client'] and observed['parameters']==ref['parameters']
            assert observed['image']==sha(a.build/mode/'src/obj-nes-100/firmware.stm')
            t=timing(folder,calendar)
            assert t['D1_bytes']==reference_time['D1_bytes']
            gains=dict(last_ACK_ms=ms(observed['last_ACK']-ref['last_ACK']),
                       dense_mean_ms=observed['dense_mean_ms']-ref['dense_mean_ms'])
            checks=dict(display951=observed['display951'][0]==3 and observed['display951'][1]<=246,
                        display952=observed['display952']<=4,display953=observed['intervals'][2]<=3,
                        wait957=observed['wait957']==0, dense=observed['dense_VB']<ref['dense_VB'],
                        last_ACK=gains['last_ACK_ms']<0)
            modes[mode]=dict(run=folder.name,schedule=observed,timeline=t,delta=gains,checks=checks,pass_all=all(checks.values()))
        cases.append(dict(boot=z['boot'],phase=phase,baseline=ref,baseline_timeline=reference_time,modes=modes))
    result=dict(cases=cases,Flash={m:(a.build/m/'src/obj-nes-100/firmware.stm').stat().st_size for m in modes},
                passed={m:all(c['modes'][m]['pass_all'] for c in cases) for m in modes},
                guards=read(a.build/'map-guards.json'),
                transport_guards={m:{k:read(a.build/f'{m}-{k}.json') for k in ('faults','seal')} for m in modes},
                source_sha={p.name:sha(p) for p in Path(__file__).parent.glob('*638.py')},
                scope='Linked Cortex-M4 and emulated 65816 with the 637 FPGA, SPI costs and ROM grant calendar.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('traces','calendar','build','out'):p.add_argument('--'+key,required=True,type=Path)
    analyze(p.parse_args())
