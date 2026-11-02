# SPDX-License-Identifier: MIT
"""Separate the 957 intra-blank work from the ARM/ROM feedback across 53 screens."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_history547 import beam
from analyze_nes_phase537 import Calendar, ROOT, csv_groups, ms, one, read, sha
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare, timeline


def last_frame(folder):
    frame=csv_groups(folder/'window.csv')[957]
    cpu=[r for r in frame if r['op']==3]
    head,entry,ack=(one(cpu,k)['clock'] for k in ('load','final212','ack'))
    dma=[r for r in cpu if r['event']=='ppu_dma' and r['clock']<entry]
    last=[r for r in cpu if r['event']=='ppu_last' and r['clock']<entry][-1]
    first=dma[0]['clock']
    sample=beam(folder)
    latch=next(r['clock'] for r in csv_groups(folder/'seal528.csv')[957]
               if r['event']=='latch' and r['clock']>=entry)
    # Coordinates are sampled by the same beam read in all four paths.
    line,h=sample['latched']
    return dict(head=head,first_DMA=first,last_byte=last['clock'],entry=entry,latch=latch,ACK=ack,
                sizes=[r['value'] for r in dma],before_SEAL_DMA_B=sum(r['value'] for r in frame if r['event']=='ppu_dma' and r['clock']<head),
                whole_frame_DMA_B=sum(r['value'] for r in frame if r['event']=='ppu_dma'),head_to_first_DMA_ms=ms(first-head),
                first_DMA_to_entry=entry-first,last_byte_to_entry=entry-last['clock'],
                entry_to_latch=latch-entry,callback_margin_clocks=(247-line)*1364-h-1,beam=sample)


def analyze(a):
    previous=read(ROOT/'analysis/supply549-verification.json')
    cal=Calendar(a.traces/'nes-service509-rom03')
    result=[]
    for i in (1,2):
        prior=previous['phases'][i-1]
        variant=prior['variants']['suffix']
        old=a.traces/f'nes-supply549-suffix{i}'
        new=a.traces/f'nes-upload550-joint{i}'
        fixed=a.traces/f'nes-upload550-fixed{i}'
        audit=a.traces/f'nes-upload550-audit{i}'
        assert all(sha(old/n)==digest for n,digest in variant['cost']['pins'].items())
        pins=read(fixed/'pins.json')
        assert pins['packets']==sha(old/'packets.jsonl') and pins['candidate_client']==sha(a.client/'sink165.sfc')
        measured=inspect_run(new,a.plans,cal,old,variant['firmware'],sha(a.client/'sink165.sfc'),first_bg_limit=3)
        audit_result=read(audit/'audit.json')
        assert audit_result['frames']==53 and audit_result['trace']==sha(new/'window.csv')
        path=timeline(new,cal)
        sections={k:last_frame(folder) for k,folder in [
            ('three',a.traces/f'nes-supply549-three{i}'),('suffix',old),('fixed',fixed/'run'),('joint',new)]}
        for sample in sections.values():
            assert sample['whole_frame_DMA_B']==sections['suffix']['whole_frame_DMA_B']
            assert sample['before_SEAL_DMA_B']+sum(sample['sizes'])==sections['suffix']['before_SEAL_DMA_B']+sum(sections['suffix']['sizes'])
        controls={'counter':prior['counter_only'],'548':prior['base548'],
                  'three':prior['variants']['three']['cost'],'suffix':variant['cost']}
        delta={name:compare(measured,ref) for name,ref in controls.items()}
        later=[g for g,b in measured['BG'].items()
               if b['relative_window']>variant['cost']['BG'][str(g)]['relative_window']]
        probe=a.traces/f'nes-upload550-gate{i}'
        assert read(probe/'audit.json')['trace']==audit_result['trace']
        with (probe/'gate550.csv').open() as f:
            latched,=[int(r['latched_v']) for r in csv.DictReader(f) if r['generation']=='957']
        gate=(225<=latched<=246 and path['display_to_head_VB']<=5 and not any(measured['waits'].values()) and
              all(sections[k]['beam']['waits']==0 for k in ('fixed','joint')) and
              all(v<0 for name in ('three','548','counter') for v in delta[name].values()) and not later)
        result.append(dict(phase=i,measured=measured,frame952=path,frame957=sections,delta=delta,
                           fixed_replay=read(fixed/'run/audit.json'),independent_replay=audit_result,
                           CPU_compared_line_957=latched,later_BG_windows=later,gate=gate))
    guards={k:read(a.traces/f'nes-upload550-{k}'/'result.json') for k in ('counts','stop','recovery')}
    assert len(guards['stop'])==7 and len(guards['recovery'])==6
    assert all(r['restored_rows']==6 and r['status']==228 for r in guards['recovery'])
    return dict(phases=result,gate=all(r['gate'] for r in result),guards=guards,client=sha(a.client/'sink165.sfc'),
                body_B=read(a.client/'build.json')['body_bytes'],ARM_SHA256=previous['builds']['suffix']['firmware'],
                scope='Two fixed starts with 53 captures, M4 instruction cost, IRQ, SPI and recorded boot ROM grants. No physical FPS.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','plans','client','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
