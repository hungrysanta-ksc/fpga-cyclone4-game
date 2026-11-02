# SPDX-License-Identifier: MIT
"""Compare receipt generation and publication with the 546 and 547 end-to-end timelines."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from analyze_nes_drain543 import delta
from analyze_nes_history547 import beam,service_windows
from analyze_nes_phase537 import Calendar,csv_groups,ms,read,sha
from analyze_nes_seal538 import inspect_run

ROOT=Path(__file__).resolve().parents[1]


def table(path):
    with path.open() as f:
        return [{k:int(v) for k,v in row.items()} for row in csv.DictReader(f)]


def sealed_bytes(folder):
    raw=False
    sizes=Counter()
    for r in csv_groups(folder/'seal528.csv')[957]:
        if r['event']=='raw_enter':raw=True
        elif r['event']=='raw_done':raw=False
        elif r['event']=='dma' and r['port']==24:
            kind='raw' if raw else 'map' if r['src']&0x7000==0x5000 else 'tile'
            sizes[kind]+=r['bytes']
    return dict(sizes)


def measure(a,i,tag,ref,controls):
    root=a.traces
    run=root/f'nes-receipt548-{tag}{i}'
    audit=root/f'nes-receipt548-{tag}-audit{i}'
    base=root/f'nes-header546-run{i}'
    generic=tag=='verified'
    fixed=root/f"nes-receipt548-{'verified-' if generic else ''}fixed{i}"
    client=a.builds/('client04' if generic else 'client02')
    assert all(sha(base/n)==v for n,v in ref['pins'].items())
    replay=read(audit/'audit.json')
    assert replay['frames']==53 and replay['trace']==sha(run/'window.csv')
    assert sha(audit/'tile532.csv')==sha(run/'tile532.csv')
    history=table(audit/'history547.csv')
    by_gen={r['g']:r for r in history}
    assert len(by_gen)==len(history)
    omitted=sum(r['omitted'] for r in history)*64
    assert all(r['omitted']==r['mask'].bit_count() and r['writes']+r['omitted']==6 for r in history)
    measured=inspect_run(run,a.plans,Calendar(a.calendar),base,controls['firmware'],sha(client/'sink165.sfc'),omitted_raw_B=omitted)
    def dma_bytes(folder):
        return {g:sum(r['value'] for r in v if r['event']=='ppu_dma') for g,v in csv_groups(folder/'window.csv').items() if g>=905}
    before,after=dma_bytes(base),dma_bytes(run)
    assert before.keys()==after.keys() and all(before[g]-after[g]==64*by_gen.get(g,{'omitted':0})['omitted'] for g in before)
    fill=table(audit/'fill548.csv');clocks=Counter()
    for f in fill:
        assert f['finish']>f['start']
        clocks[f['g']]+=f['finish']-f['start']
    warm=[r for r in history if r['prior']>=0]
    compare={k:delta(measured,src) for k,src in controls['rows'].items()}
    actual_beam=beam(run)
    gate=(actual_beam['waits']==0 and not any(measured['waits'].values()) and
          all(d['dense_ms']<0 and d['dense_VB']<0 and d['last_ACK_ms']<0 and not d['later_BG_windows']
              for n,d in compare.items() if n!='547'))
    assert read(fixed/'pins.json')['packets']==ref['pins']['packets.jsonl']
    fixed_proof=read(fixed/'run/audit.json');assert fixed_proof['frames']==53
    bound=None
    if not generic:
        bind=root/f'nes-receipt548-bind{i}'
        bound=read(bind/'pins.json')
        assert bound['source_client']==sha(client/'sink165.sfc')
        assert bound['candidate_client']==sha(a.builds/'client05/sink165.sfc')
        assert sha(bind/'run/window.csv')==sha(run/'window.csv')
        assert sha(bind/'run/tile532.csv')==sha(run/'tile532.csv')
    windows=service_windows(run);base_windows=service_windows(base)
    return dict(candidate=measured,delta=compare,beam=actual_beam,fixed_beam=beam(fixed/'run'),
                SEAL_957_B=dict(base=sealed_bytes(base),candidate=sealed_bytes(run)),
                dense_split={g:dict(base=base_windows[g],candidate=windows[g]) for g in range(951,956)},
                fixed_ACK_delta_ms=ms(fixed_proof['last_ACK_delta_clocks']),omitted_B=omitted,
                warm_SEAL_ms=mean(ms(r['finish']-r['prepare']) for r in warm),
                warm_receive_ms=mean(ms(clocks[r['g']]) for r in warm),
                mean_51_ms=mean(v['interval_ms'] for v in windows.values()),
                warm_VBlank_delta={k:sum(v[k]-base_windows[g][k] for g,v in windows.items()) for k in ('before_head','after_head')},
                history=history,target=by_gen[957],replay=replay,fill_SHA256=sha(audit/'fill548.csv'),
                history_SHA256=sha(audit/'history547.csv'),fault_revision_replay=bound,gate=gate)


def analyze(a):
    ref=read(ROOT/'analysis/header546-verification.json')
    old=read(ROOT/'analysis/history547-verification.json')
    trimmed=read(ROOT/'analysis/drain543-verification.json')
    original=read(ROOT/'analysis/first539-verification.json')
    fw=ref['firmware_SHA256'];assert fw==read(ROOT/'analysis/windows541-verification.json')['firmware_SHA256']
    phases=[]
    for i in (1,2):
        prior=ref['phases'][i-1]['candidate']
        controls=dict(firmware=fw,rows={'546':prior,'547':old['phases'][i-1]['shared']['candidate'],
                                        'trimmed':trimmed['phases'][i-1]['base'],'MMC540':original['phases'][i-1]['row']})
        phases.append(dict(phase=i,**{n:measure(a,i,tag,prior,controls) for n,tag in [('binary','run'),('any','verified')]}))
    checks=[read(a.traces/f'nes-receipt548-final-check{i}/result.json') for i in range(4)]
    assert [len(v) for v in checks[:3]]==[8,7,22]
    assert all(r['status']==228 for cases in checks[:2] for r in cases)
    assert checks[3]['masks']=={'905':0,'906':0,'909':0,'910':0,'911':63,'912':32}
    recovery=read(a.traces/'nes-receipt548-recovery01/result.json')
    assert len(recovery)==6 and all(r['status']==228 and r['restored_rows']==6 for r in recovery)
    small_recovery=read(a.traces/'nes-receipt548-binary-recovery/result.json')
    assert recovery==small_recovery
    menu=read(a.builds/'menu01.json');assert menu['firmware']==fw and all(v['released']==int(k=='normal') for k,v in menu['rows'].items())
    return dict(phases=phases,gate=all(p['any']['gate'] for p in phases),checks=checks,recovery=recovery,menu=menu,
                builds={n:dict(body_B=len((a.builds/n/'body.bin').read_bytes()),receipt_B=read(a.builds/n/'build.json')['receipt_B'],
                               SHA256=sha(a.builds/n/'sink165.sfc')) for n in ('client02','client04','client05')},
                firmware=fw,scope='Two 53-frame schedules with the same trimmed counter ARM, SPI, IRQ, two slots and 65816. Fixed captured inputs and repeating boot ROM grants.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','builds','plans','calendar','out'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();result=analyze(a)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    for p in result['phases']:
        r=p['any'];print(p['phase'],r['beam'],r['delta']['546'],r['gate'])
