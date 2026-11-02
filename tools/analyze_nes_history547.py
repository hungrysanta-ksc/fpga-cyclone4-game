# SPDX-License-Identifier: MIT
"""Join per-bank ACK/WRAM evidence to actual DMA totals, beam samples and both ARM timelines."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from analyze_nes_drain543 import delta
from analyze_nes_phase537 import Calendar,csv_groups,ms,one,read,sha
from analyze_nes_seal538 import inspect_run

ROOT=Path(__file__).resolve().parents[1]


def beam(folder):
    samples=csv_groups(folder/'seal528.csv')[957]
    cpu=[r for r in csv_groups(folder/'window.csv')[957] if r['op']==3]
    entry=one(cpu,'final212')
    latches=[r for r in samples if r['event']=='latch' and r['clock']>=entry['clock']]
    waits=sum(r['event']=='wait169' and r['clock']>=entry['clock'] for r in cpu)
    if not latches:
        assert not waits
        return dict(entry=entry['line'],waits=0,latched=None)
    latch,=latches
    return dict(entry=entry['line'],waits=waits,latched=[latch['line'],latch['h']],
                late_clocks=max(0,(latch['line']-247)*1364+latch['h']+1))


def service_windows(folder):
    groups=csv_groups(folder/'window.csv')
    previous=one([r for r in groups[906] if r['op']==3],'reveal')
    result={}
    for gen in range(907,958):
        seal=[r for r in groups[gen] if r['op']==3]
        head,display=(one(seal,k) for k in ('load','reveal'))
        result[gen]=dict(before_head=head['frame']-previous['frame'],after_head=display['frame']-head['frame'],
                         interval_ms=ms(display['clock']-previous['clock']))
        previous=display
    return result


def repeat_coverage(folder,rows):
    # Offline cost bound for the next candidate. Only a single accepted,
    # uniform section-5 repeat covering the entire row counts as evidence.
    fills={}
    for line in (folder/'packets.jsonl').read_text().splitlines():
        b=bytes.fromhex(json.loads(line)[2])
        if b[0] not in (4,5) or b[1]!=5 or b[16]!=b[17]:
            continue
        gen=int.from_bytes(b[8:10],'little')
        at=int.from_bytes(b[10:12],'little')
        end=at+int.from_bytes(b[14:16],'little')
        for row in range(6):
            first=1121+row*64
            if at<=first and first+64<=end:
                assert (gen,row) not in fills
                fills[gen,row]=b[16]
    total=0
    target=[]
    for r in rows:
        for row in range(6):
            current=(r['g'],row)
            if current in fills and fills.get((r['prior'],row))==fills[current]:
                assert r['mask']&(1<<row)
                total+=1
                if r['g']==957:target.append(row)
    return dict(rows_provable=total,target957=target)


def checks(args,fast):
    tag='fast-check' if fast else 'check'
    evidence=[read(args.traces/f'nes-history547-{tag}{i}/result.json') for i in range(3)]
    assert [len(s) for s in evidence]==[8,7,22]
    assert all(r['status']==228 and r['commits']==r['generation']-905 for group in evidence[:2] for r in group)
    recovered=read(args.traces/('nes-history547-fast-check3' if fast else 'nes-history547-recovery01')/'result.json')
    assert len(recovered)==4 and all(r['writes_after_recovery']==6 and r['status']==228 for r in recovered)
    counts=read(args.traces/f'nes-history547-counts{int(fast)}/result.json')
    assert counts['masks']=={'905':0,'906':0,'909':0,'910':0,'911':63,'912':61}
    return dict(negative=evidence,recovery=recovered,transitions=counts)


def measure(args,i,fast,before,fw):
    prefix='fast' if fast else 'run'
    root=args.traces
    run=root/f'nes-history547-{prefix}{i}'
    base=root/f'nes-header546-run{i}'
    audit=root/f"nes-history547-{'fast-' if fast else ''}audit{i}"
    fixed=root/f"nes-history547-{'fast-' if fast else ''}fixed{i}"
    client=args.builds/('client03' if fast else 'client02')
    digest=sha(client/'sink165.sfc')
    proof=read(audit/'audit.json')
    assert proof['trace']==sha(run/'window.csv') and proof['frames']==53
    assert sha(run/'tile532.csv')==sha(audit/'tile532.csv')
    with (audit/'history547.csv').open() as f:
        rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
    assert all(r['omitted']==r['mask'].bit_count() and r['writes']+r['omitted']==6 for r in rows)
    seen={r['g']:r for r in rows}
    assert len(seen)==len(rows)
    skipped=sum(r['omitted'] for r in rows)*64
    result=inspect_run(run,args.plans,Calendar(args.calendar),base,fw,digest,omitted_raw_B=skipped)
    # Reconcile the actual PPU transactions for EVERY generation, independently
    # of total bytes, including frames with no eligible compact image.
    def bytes_by_frame(folder):
        return {g:sum(r['value'] for r in events if r['event']=='ppu_dma') for g,events in csv_groups(folder/'window.csv').items() if g>=905}
    old,new=bytes_by_frame(base),bytes_by_frame(run)
    assert old.keys()==new.keys() and all(old[g]-new[g]==64*seen.get(g,{'omitted':0})['omitted'] for g in old)
    assert read(fixed/'pins.json')['packets']==before['pins']['packets.jsonl']
    fixed_proof=read(fixed/'run/audit.json')
    assert fixed_proof['frames']==53
    current=beam(run)
    baseline_windows=service_windows(base)
    windows=service_windows(run)
    splits={k:sum(w[k]-baseline_windows[g][k] for g,w in windows.items()) for k in ('before_head','after_head')}
    return dict(candidate=result,delta=delta(result,before),gate_957=current['waits']==0,
                beam=current,fixed_beam=beam(fixed/'run'),fixed_ACK_delta_ms=ms(fixed_proof['last_ACK_delta_clocks']),
                omitted_B=skipped,target=seen[957],history_rows=rows,
                offline_repeat_coverage=repeat_coverage(run,rows),
                warm_VBlank_delta=splits,mean_51_ms=mean(w['interval_ms'] for w in windows.values()),
                preparation_ms=mean(ms(r['finish']-r['prepare']) for r in rows if r['prior']>=0),
                exact_replay=proof,history_SHA256=sha(audit/'history547.csv'))


def analyze(args):
    ref=read(ROOT/'analysis/header546-verification.json')
    original=read(ROOT/'analysis/first539-verification.json')
    phases=[]
    for i in (1,2):
        before=ref['phases'][i-1]['candidate']
        assert all(sha(args.traces/f'nes-header546-run{i}'/n)==h for n,h in before['pins'].items())
        p=dict(phase=i,baseline=beam(args.traces/f'nes-header546-run{i}'))
        for tag,fast in [('nested',False),('shared',True)]:
            r=measure(args,i,fast,before,ref['firmware_SHA256'])
            original_delta=delta(r['candidate'],original['phases'][i-1]['row'])
            r['versus_MMC540']=original_delta
            r['promotion_gate']=r['gate_957'] and not any(r['candidate']['waits'].values()) and all(
                v['dense_VB']<0 and v['dense_ms']<0 and v['last_ACK_ms']<0 and not v['later_BG_windows']
                for v in (r['delta'],original_delta))
            p[tag]=r
        phases.append(p)
    return dict(phases=phases,checks={tag:checks(args,f) for tag,f in [('nested',False),('shared',True)]},
                builds={name:{'ROM_body_B':len((args.builds/name/'body.bin').read_bytes()),'SHA256':sha(args.builds/name/'sink165.sfc')} for name in ('client02','client03')},
                shadow_B=768,extra_cartridge_RAM_B=0,firmware=ref['firmware_SHA256'],
                scope='Actual linked ARM / SPI / IRQ and actual 65816 simulation with fixed captures and boot-derived ROM grants.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','builds','plans','calendar','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=analyze(args)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    for p in result['phases']:
        for tag in ('nested','shared'):
            r=p[tag];print(p['phase'],tag,r['delta']['last_ACK_ms'],r['beam'],r['promotion_gate'])
