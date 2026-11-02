# SPDX-License-Identifier: MIT
"""Bind the three DMA cursor comparisons to independent replays and STOP guards."""
import argparse
import json
from pathlib import Path
from statistics import mean
from analyze_nes_dma542 import partition
from analyze_nes_phase537 import csv_groups, read, sha


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('private','traces','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();base=[];results={}
    for phase in (1,2):
        rows=partition(a.traces/f'nes-first539-row{phase}')
        base.append(dict(phase=phase,per_frame=rows,mean_ms={
            k:mean(r[k] for r in rows.values()) for k in ('output_to_head_ms','SEAL_to_ACK_ms','checks_ms','serviced_VBlank_wait_ms','other_setup_control_ms','final_wait_ms')},
            mean_DMA_ms=mean(sum(r['DMA_ms'].values()) for r in rows.values())))
        steady=[r for g,r in rows.items() if g>=907]
        base[-1]['after_first_two']=dict(frames=[907,957],mean_ms={
            k:mean(r[k] for r in steady) for k in ('output_to_head_ms','SEAL_to_ACK_ms','checks_ms','serviced_VBlank_wait_ms','other_setup_control_ms','final_wait_ms')},
            mean_DMA_ms=mean(sum(r['DMA_ms'].values()) for r in steady))
    for tag,client,guard in [('raw','client03','01'),('reg','client04','02'),('cursor','client05','03')]:
        result=read(a.private/f'{tag}-analysis.json')
        build=read(a.private/client/'build.json')
        for phase,row in enumerate(result['phases'],1):
            row.pop('base_partition')
            folder=a.traces/f'nes-dma542-{tag}{phase}'
            audit=a.traces/f'nes-dma542-audit-{tag}{phase}'
            proof=read(audit/'audit.json')
            assert proof['frames']==53 and proof['trace']==sha(folder/'window.csv')
            assert sha(audit/'tile532.csv')==sha(folder/'tile532.csv')
            row['independent_replay']=proof
            row['independent_replay_pins']={n:sha(audit/n) for n in ('audit.json','tile532.csv','window.csv')}
            def ack_frames(path):
                return {g:next(r['frame'] for r in v if r['op']==3 and r['event']=='ack') for g,v in csv_groups(path).items() if g>=905}
            before=ack_frames(a.traces/f'nes-first539-row{phase}'/'window.csv');after=ack_frames(folder/'window.csv')
            row['changed_interval_VB']={g:[before[g]-before[g-1],after[g]-after[g-1]] for g in range(906,958) if before[g]-before[g-1]!=after[g]-after[g-1]}
        tests={}
        for kind,count in [('stop',7),('priority',22)]:
            f=a.traces/f'nes-dma542-{kind}{guard}'/'result.json';rows=read(f)
            assert len(rows)==count
            if kind=='stop':assert all(r['status']==0xe4 for r in rows)
            tests[kind]=dict(cases=count,SHA256=sha(f),rows=rows)
        result.update(body_B=build['body_bytes'],mapped_program_B=5120,new_WRAM_B=0,
                      client_SHA256=sha(a.private/client/'sink165.sfc'),guards=tests)
        assert not result['gate']  # No retrospective relaxation of the dense/whole-time gate.
        results[tag]=result
    service=a.traces/'nes-dma542-service03'/'result.json'
    assert read(service)==dict(passed=True,cases=8)
    fixed={}
    for tag,run in [('raw','fixed02'),('reg','fixed03')]:
        f=a.traces/f'nes-dma542-{run}'
        fixed[tag]=dict(pins=read(f/'pins.json'),audit=read(f/'run/audit.json'))
    out=dict(baseline='MMC540; same executable runtime as 539 ARM01 / 538 client04',
             frames=[905,957],cost_frames=[906,957],baseline_partition=base,candidates=results,
             service_guard=dict(result=read(service),SHA256=sha(service)),fixed_arrivals=fixed,
             selected=None,retain='MMC540',new_hardware_package=False,new_Quartus_run=False,
             interpretation='Cursor with original service saves one VBlank across 53 screens in both phases, at 919/939 respectively. Dense 951..955 remains 30 VBlank and 957 still waits once; not a new sustained-play speed claim.',
             next='Test one existing checked map queue drain before later ordinary traffic. Charge all added E0/ARM/IRQ time; no timer sleep or DMA-completion assumption.',
             future_windows=dict(counter='display_5_40_55',seconds=[[5,40],[40,55]],evidence='analysis/windows541-verification.json'),
             scope='Actual linked ARM and 65816 with shared SPI, SysTick and 2-slot timing; repeated boot ROM calendar. No new physical FPS/menu/FIT claim.')
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')
