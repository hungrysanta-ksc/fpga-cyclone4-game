"""Match MMC666 work and partition the actual linked replay without rescaling DWT."""
import argparse
from collections import Counter
import json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_frontier536 import contents
from analyze_nes_output615 import read, sha, ms, csv_groups, one
from check_nes_fault641 import ROOT, evidence
from nes_schedule492 import funcs


def scans(folder):
    counts=Counter();instructions=Counter()
    for e in read(folder/'events.json'):
        if e['event']=='scan668':
            counts[e['generation']]+=1;instructions[e['generation']]+=e['instructions']
    return dict(calls=dict(counts),instructions=dict(instructions),
                modeled_CPI2_ms={g:n*2/84000 for g,n in instructions.items()})


def analyze(a):
    physical=evidence('hardware667-mmc666.json')
    package=evidence('trial666-package.json')
    selected=evidence('entry665-verification.json')
    assert sha(a.base_arm/'obj-nes-100/firmware.stm')==package['firmware_SHA256']
    assert funcs(a.base_arm/'obj-nes-100/sd2snes.elf')==funcs(a.old_arm/'obj-nes-100/sd2snes.elf')
    assert sha(a.client/'sink165.sfc')==selected['client_SHA256']
    changed={p.name:sha(p) for p in a.base_arm.glob('nes_*.[ch]') if sha(p)!=sha(a.arm/p.name)}
    assert set(changed)=={'nes_native_sink165.c'}
    fresh=a.traces/'nes-output668-base1'
    assert read(fresh/'joint.json')['frames']==read(a.traces/'nes-entry665-a1/joint.json')['frames']
    assert sha(fresh/'client.sfc')==sha(a.client/'sink165.sfc')
    phases={}
    for phase in (1,2):
        base=a.traces/f'nes-entry665-a{phase}'
        candidate=a.traces/f'nes-output668-{a.mode}{phase}'
        rows={k:trace(p,a.traces/f'nes-front638-both{phase}h') for k,p in (('base',base),('candidate',candidate))}
        work={g:r['work'] for g,r in rows['base']['frames'].items()}
        assert work=={g:r['work'] for g,r in rows['candidate']['frames'].items()}
        assert contents(base)[1]==contents(candidate)[1]
        j=read(candidate/'joint.json')
        assert j['firmware_SHA256']==sha(a.arm/'obj-nes-100/firmware.stm')
        assert sha(candidate/'client.sfc')==sha(a.client/'sink165.sfc')
        assert j['parameters']==read(base/'joint.json')['parameters']
        b,c=rows['base'],rows['candidate']
        dense=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms']
        ack=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        protected=(0<c['intervals'][952]['VBlank']<=3 and c['intervals'][957]['final_waits']==0 and
                   c['details'][951]['marks']['reveal']['line']<=246)
        regress=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        waits=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        diagnostic={}
        for key,folder in (('base',base),('candidate',candidate)):
            cpu=csv_groups(folder/'window.csv')
            seal=[r for r in cpu[911] if r['op']==3]
            diagnostic[key]=dict(costs=rows[key]['frames'][911],
                previous_reveal=one([r for r in cpu[910] if r['op']==3],'reveal'),
                marks={name:one(seal,name) for name in ('load','upload165_entry','final212','reveal','ack')})
        for r in rows.values():
            r.pop('frames')
            # Raw packet/CPU observations remain in the hashed private replay.
            # Publish the causal 954/957 clocks, not four duplicate full traces.
            for g,d in r['details'].items():
                packets=d.pop('packets')
                if g in (954,957):
                    d['packet_clocks']=[{k:v[k] for k in ('op','section','offset','start','push','load','ack')} for v in packets]
        phases[phase]=dict(runs=rows,matched_work=work,dense_delta_ms=dense,last_ACK_delta_ms=ack,
                           interval_regressions=regress,new_final_waits=waits,protected=protected,
                           improves_both=protected and dense<0 and ack<0,scan=scans(candidate),
                           frame911=diagnostic,
                           pins={p.name:sha(p) for p in candidate.iterdir() if p.name in ('joint.json','events.json','window.csv','seal528.csv','packets.jsonl','obj-phases.json')})
    checks={name:read(a.probe/(name+'.json')) for name in ('scan-guards','routing','rx','seal','menu')}
    search=checks['scan-guards']
    assert search['passed'] and search['cases']==464
    assert search['runs'][1]['firmware']==sha(a.arm/'obj-nes-100/firmware.stm')
    checks['scan-guards']=dict(passed=True,cases=search['cases'],SHA256=sha(a.probe/'scan-guards.json'),
        runs=[dict(label=r['label'],firmware=r['firmware'],instructions=sum(c['instructions'] for c in r['cases'])) for r in search['runs']])
    if a.mode=='drain':
        checks['map-drain']=read(a.probe/'map-drain.json')
        assert checks['map-drain']['firmware']==sha(a.arm/'obj-nes-100/firmware.stm')
    for n in ('routing','rx','seal','menu'):assert checks[n]['firmware']==sha(a.arm/'obj-nes-100/firmware.stm')
    recovery={}
    for fault in ('none','program','done','busy','token'):
        r=read(a.probe/f'base-{fault}/result.json')
        assert r['passed'] and r['firmware_sha256']==sha(a.arm/'obj-nes-100/firmware.stm')
        assert r['safe_return']==r['base_restored']==int(fault=='none')
        recovery[fault]=r
    boards=selected['boards']['entry665']
    manifest=read(a.board/'inputs665.json')
    assert all(sha(a.board/name)==digest for name,digest in manifest['inputs'].items())
    assert all(sha(a.board/'output_files'/name)==digest for name,digest in boards['timing']['pins'].items())
    sizes={name:dict(zip(('text','data','bss'),map(int,(src.parent/'size.log').read_text().splitlines()[1].split()[:3])))
           for name,src in (('base',a.base_arm),('candidate',a.arm))}
    assert all(sizes['base'][key]==sizes['candidate'][key] for key in ('data','bss'))
    result=dict(baseline='MMC666',candidate=a.mode,merged_PR154='3f8292795b8a5e53d6cf250fcc568223e748a3d6',
                physical_output_ms=physical['phases']['output_final_ack']['ms_per_display'],
                physical_evidence=sha(ROOT/'analysis/hardware667-mmc666.json'),
                phases=phases,baseline_scan=scans(fresh),checks=checks,recovery=recovery,
                timing_gate=all(p['improves_both'] for p in phases.values()),
                no_new_waits=all(not p['new_final_waits'] for p in phases.values()),
                firmware=sha(a.arm/'obj-nes-100/firmware.stm'),changed_ARM_sources=changed,
                Flash_B=(a.arm/'obj-nes-100/firmware.stm').stat().st_size,
                Flash_free_B=212992-(a.arm/'obj-nes-100/firmware.stm').stat().st_size,
                ARM_sections=sizes,
                unchanged_board=boards,unchanged_client=selected['client_SHA256'],
                no_new_FPGA_synthesis=True,capture_recovery='Unchanged selected665 HDL/constraints and MMC666 physical reject/recovery evidence.',
                scope='Actual linked M4/65816 with CPI2/IRQ/shared SPI and repeated measured ROM calendar. Matched 53 captures per start, not the unsynchronized physical playthrough. Pre-SEAL CPU/DMA overlaps ARM issuance; nested costs are not added. Physical 26.84ms cannot be partitioned from this log alone.',
                sources={p.name:sha(p) for p in [*(ROOT/'tools').glob('*output668.py'),ROOT/'tools/check_nes_map668.py']})
    result['selected']=a.mode if result['timing_gate'] and result['no_new_waits'] else 'MMC666'
    result['new_delivery']=False
    if a.linear_result:
        old=read(a.linear_result)
        assert old['candidate']=='linear' and old['physical_evidence']==result['physical_evidence']
        assert old['sources']==result['sources']
        result['linear_candidate']=old
        result['linear_candidate_SHA256']=sha(a.linear_result)
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(timing_gate=result['timing_gate'],Flash_free_B=result['Flash_free_B'],
                         phases={n:{k:p[k] for k in ('dense_delta_ms','last_ACK_delta_ms','interval_regressions','new_final_waits','protected')} for n,p in phases.items()}),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','probe','base-arm','old-arm','arm','client','board','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mode',default='linear')
    p.add_argument('--linear-result',type=Path)
    analyze(p.parse_args())
