# SPDX-License-Identifier: MIT
"""Disjoint host-call and consumer costs on paired, bit-identical MMC529 workloads."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from analyze_nes_map526 import ROOT, ms, read, sha
from analyze_nes_quiet528 import packet_content
from analyze_nes_supply485_hardware import fields

WARM=range(907,958)
DENSE=range(951,956)
KINDS=('tile','map','raw')


def csv_groups(path):
    result=defaultdict(list)
    with path.open() as f:
        for row in csv.DictReader(f):
            result[int(row['g'])].append({k:v if k=='event' else int(v) for k,v in row.items()})
    return result


def one(rows,name):
    row,=[r for r in rows if r['event']==name]
    return row


def overlap(lo,hi,left,right):
    return max(0,min(hi,right)-max(lo,left))


def waits(rows):
    pending=None
    result=[]
    for r in rows:
        if r['event']=='wait169':
            assert pending is None
            pending=r['clock']
        elif pending is not None and (r['event'].startswith('wait_return_') or r['event']=='final_upload212_same_blank212'):
            result.append((pending,r['clock']))
            pending=None
    assert pending is None
    return result


def kind(bank,dst):
    bg,obj,raw,map_base=(0xc000,0x8000,0x9000,0xa000) if bank else (0,0x4000,0x5000,0x6000)
    if dst==raw:return 'raw'
    if map_base<=dst<map_base+4096:return 'map'
    if bg<=dst<bg+16384 or obj<=dst<obj+4096:return 'tile'
    raise ValueError(f'Unexpected command destination {dst:x} in bank {bank}')


def prior_blank_windows(sample,frame,lo,hi,last_line):
    """Real NTSC scanlines, anchored at a captured PPU DMA in VBlank."""
    assert 225<=sample['line']<262 and 0<=sample['h']<1364
    begin=sample['clock']-(sample['line']-225)*1364-sample['h']
    if frame%2==0 and sample['line']>240:begin+=4
    assert hi<=sample['clock']
    while begin+(last_line-224)*1364>lo:
        stop=begin+(last_line-224)*1364-(4 if frame%2==0 and last_line>=240 else 0)
        if min(hi,stop)>max(lo,begin):yield max(lo,begin),min(hi,stop)
        frame-=1
        begin-=262*1364-(4 if frame%2==0 else 0)


def opportunity(available,cutoff,last_line,anchor,frame,gaps,grants):
    # Optimistic upper bound: no credit/validation/beam-probe/after-DMA
    # bookkeeping is charged. Already executing idle grants cannot be reused.
    spans=[]
    for l,h in prior_blank_windows(anchor,frame,available,cutoff,last_line):
        for a,b in gaps:
            left,right=max(l,a),min(h,b)
            if right<=left:continue
            for x,y in grants:
                if x>=right:break
                if y<=left:continue
                if left<x:spans.append(x-left)
                left=max(left,y)
            if left<right:spans.append(right-left)
    return dict(total_upper_clocks=sum(spans),longest_upper_clocks=max(spans,default=0))


def breakdown(g,events,cpu,samples,packets,arrivals):
    start=one(events,'output_enter531')['clock']
    end=one(events,'output_return531')['clock']
    seal=[r for r in cpu if r['op']==3]
    load=one(seal,'load')['clock']
    final=one(seal,'final212')['clock']
    ack=one(seal,'ack')['clock']
    assert start<load<final<ack<=end
    w=waits(seal)
    first_half=[(a,b) for a,b in w if a<final]
    second_half=[(a,b) for a,b in w if a>=final]
    assert len(second_half)<=1
    account=Counter()
    account['before_SEAL_load']=load-start
    account['post_ACK']=end-ack
    account['final_blank_wait']=sum(b-a for a,b in second_half)
    account['final_display_work']=ack-final-account['final_blank_wait']
    # Count actual command service, omitting any wait within the command.
    cmds=[r for r in samples if r['event']=='command']
    assert cmds[-1]['bytes']==-1 and all(r['bytes']>=0 for r in cmds[:-1])
    account['checks_and_list']=cmds[0]['clock']-load+final-cmds[-1]['clock']
    account['upload_blank_wait']=sum(b-a for a,b in first_half)
    first_resume=first_half[-1][1] if first_half else cmds[0]['clock']
    transfers=[r for r in seal if r['event']=='ppu_dma' and r['clock']<final]
    ends=[r for r in seal if r['event']=='ppu_last' and r['clock']<final]
    assert len(transfers)==len(ends)
    byte_count=Counter()
    late_tail=Counter()
    late_writes=Counter()
    rows=[]
    used=0
    for r,next_r in zip(cmds,cmds[1:]):
        k=kind(r['bank'],r['bytes'])
        lo,hi=r['clock'],next_r['clock']
        active=hi-lo-sum(overlap(lo,hi,a,b) for a,b in first_half)
        dma=[(v,z) for v,z in zip(transfers,ends) if lo<=v['clock']<hi]
        assert dma and all(v['clock']<z['clock']<hi for v,z in dma)
        advance,=[x['clock'] for x in samples if x['event']=='raw_done' and lo<=x['clock']<hi]
        assert advance>dma[-1][1]['clock']  # Common command advance, also reached after normal DMA.
        raw_entry=[x['clock'] for x in samples if x['event']=='raw_enter' and lo<=x['clock']<hi]
        assert bool(raw_entry)==(k=='raw')
        used+=len(dma)
        span=sum(z['clock']-v['clock'] for v,z in dma)
        n=sum(v['value'] for v,z in dma)
        byte_count[k]+=n
        account[k+'_dma']+=span
        account[k+'_control']+=active-span
        after=max(0,hi-max(lo,first_resume))
        late_tail[k]+=after
        late_writes[k]+=sum(overlap(first_resume,final,v['clock'],z['clock']) for v,z in dma)
        rows.append(dict(kind=k,dst=r['bytes'],B=n,DMAs=len(dma),active=active,
                         after_last_upload_wait=after,wire_span=span))
    assert used==len(transfers)
    for k in KINDS:
        for suffix in ('_dma','_control'):
            account.setdefault(k+suffix,0)
    assert all(v>=0 for v in account.values()) and abs(sum(account.values())-(end-start))<1e-5
    # CPU service and idle intervals overlap ARM/SPI work. These sub-buckets
    # explain before_SEAL_load and must not be added to the outer partition.
    heads={};pre=Counter()
    for r in cpu:
        if r['event']=='load':heads[r['index']]=r
        if r['event']=='ack':
            h=heads.pop(r['index'])
            span=overlap(start,load,h['clock'],r['clock'])
            op=h['op'];sec=h['section']
            group='bulk' if op==7 else 'map' if sec==2 else 'section5' if sec==5 else 'other'
            pre[group]+=span
    assert not heads
    pre['no_head']=account['before_SEAL_load']-sum(pre.values())
    assert pre['no_head']>=0
    decision=next((r['event'] for r in seal if r['event'] in ('borrow516','fresh516')),'credit')
    credit=one(samples,'final_credit')['bytes']
    assert (credit>=1568)==(decision=='credit') and bool(second_half)==(decision=='fresh516')
    latch=[r for r in samples if r['event']=='latch']
    miss=None
    if decision=='fresh516' and latch and 247<=latch[-1]['line']<=261:
        miss=(latch[-1]['line']-247)*1364+latch[-1]['h']+1
    # Coverage of the actual compact raw bytes at ordinary packet ACKs.
    hd=packets[one(seal,'load')['index']-1]
    raw_size=int.from_bytes(hd[26:28],'little')-1121-249 if int.from_bytes(hd[38:40],'little') else 0
    obtained=set();raw_ready=None;raw_rows={}
    for r in cpu:
        if r['event']!='ack' or r['section']!=5 or r['op'] not in (2,4,5):continue
        b=packets[r['index']-1];offset=int.from_bytes(b[10:12],'little')
        size=int.from_bytes(b[12:14] if b[0]==2 else b[14:16],'little')
        obtained.update(range(max(1121,offset),min(1121+raw_size,offset+size)))
        if raw_size in (192,384):
            for at in range(1121,1121+raw_size,64):
                if at not in raw_rows and all(p in obtained for p in range(at,at+64)):raw_rows[at]=r['clock']
        if raw_size and len(obtained)==raw_size and raw_ready is None:raw_ready=r
    assert not raw_size or raw_ready is not None
    first_dma=next(r for r in samples if r['event']=='dma')
    frame=next(r['frame'] for r in seal if r['event']=='ppu_dma')
    cutoff=arrivals[one(seal,'load')['index']-1]
    gaps=[];grants=[];grant=None;coverage=defaultdict(dict)
    early_dma=Counter()
    for r in cpu:
        if r['event']=='idle524':
            assert grant is None
            grant=r
            dma_start=None
        elif r['event']=='ppu_dma' and r['op']==-1:
            assert grant is not None
            dma_start=r['clock']
        elif r['event']=='ppu_last' and r['op']==-1:
            assert grant is not None and dma_start is not None
            grants.append((grant['clock'],r['clock']))
            k='map' if grant['value']>=65536 else 'tile'
            early_dma[k]+=overlap(start,load,dma_start,r['clock'])
            grant=None
        if r['event']!='ack' or r['op'] in (1,3):continue
        idx=r['index']
        if arrivals[idx]>r['clock']:gaps.append((r['clock'],arrivals[idx]))
        b=packets[idx-1];sec=b[1]
        if not (b[0]==7 or (sec==2 and b[0] in (2,4))):continue
        offset=int.from_bytes(b[10:12],'little')
        size=int.from_bytes(b[12:14] if b[0]==2 else b[14:16],'little')
        unit=(16,32,64)[sec]
        assert offset%unit==size%unit==0
        for pos in range(offset,offset+size,unit):
            coverage[sec][pos]=r['clock']
    assert grant is None
    assert sum(early_dma.values())<=pre['no_head']
    raw_room=opportunity(raw_ready['clock'],cutoff,261,first_dma,frame,gaps,grants) if raw_ready else None
    raw_row_rooms=[opportunity(t,cutoff,261,first_dma,frame,gaps,grants) for _,t in sorted(raw_rows.items())]
    bank=cmds[-1]['bank']
    bases=(0xc000,0x8000,0xa000) if bank else (0,0x4000,0x6000)
    for item in rows:
        if item['kind']=='raw':continue
        sec=2 if item['kind']=='map' else (0 if bases[0]<=item['dst']<bases[0]+16384 else 1)
        offset=item['dst']-bases[sec];unit=(16,32,64)[sec]
        receipts=[coverage[sec][p] for p in range(offset,offset+item['B'],unit)]
        item['first_unit_room']=opportunity(receipts[0],cutoff,254 if sec==2 else 232,first_dma,frame,gaps,grants)
        item['whole_command_room']=opportunity(max(receipts),cutoff,254 if sec==2 else 232,first_dma,frame,gaps,grants)
    return dict(g=g,call_ms=ms(end-start),ms={k:ms(v) for k,v in account.items()},
                pre_load_ms={k:ms(v) for k,v in pre.items()},
                pre_load_idle_DMA_ms={k:ms(early_dma[k]) for k in ('tile','map')},commands=rows,seal_bytes=dict(byte_count),
                decision=decision,final_credit=credit,miss_clocks=miss,
                last_blank_command_clocks=dict(late_tail),last_blank_DMA_clocks=dict(late_writes),
                catch_up_ms=ms(miss) if miss else None,
                raw_ready_to_load_ms=ms(load-raw_ready['clock']) if raw_ready else None,
                raw_ready_line=raw_ready['line'] if raw_ready else None,
                raw_room=raw_room,raw_row_rooms=raw_row_rooms,
                idle_grants_after_raw=sum(raw_ready['clock']<=r['clock']<load and r['event']=='idle524' for r in cpu) if raw_ready else None)


def summarize(rows):
    keys=rows[0]['ms']
    late=[r for r in rows if r['miss_clocks'] is not None]
    final_waits=[r['ms']['final_blank_wait'] for r in rows if r['ms']['final_blank_wait']]
    return dict(frames=len(rows),call_ms=mean(r['call_ms'] for r in rows),
                means={k:mean(r['ms'][k] for r in rows) for k in keys},
                pre_load_means={k:mean(r['pre_load_ms'].get(k,0) for r in rows) for k in ('bulk','map','section5','other','no_head')},
                pre_load_idle_DMA_means={k:mean(r['pre_load_idle_DMA_ms'][k] for r in rows) for k in ('tile','map')},
                decisions=dict(Counter(r['decision'] for r in rows)),
                late_beam_frames=len(late),
                conditional_crossings={k:sum(r['last_blank_command_clocks'].get(k,0)>=r['miss_clocks'] for r in late) for k in KINDS},
                raw_already_complete_no_empty_blank=sum(r['raw_room'] is not None and r['raw_room']['total_upper_clocks']==0 for r in late),
                mean_wait_when_taken=mean(final_waits) if final_waits else None)


def analyze(a):
    release=read(ROOT/'analysis/flash529-verification.json')
    hw=read(ROOT/'analysis/hardware530-mmc529.json')
    budget=fields(a.budget.read_text(encoding='utf-8-sig'))
    assert hw['source_SHA256'][a.budget.name]==sha(a.budget)
    calls,_,high,low,_=map(int,budget['cost_phase_02'].split(','))
    freq=int(budget['cost_clock_hz'])
    physical=(high*2**32+low)*1000/(freq*calls)
    assert calls==hw['display']['completed'] and physical==hw['phases']['output_final_ack']['ms_per_display']
    poll=list(map(int,budget['cost_poll_2'].split(',')))
    phases=[]
    for folder,baseline,ref in zip(a.runs,a.baseline,release['phases']):
        result=read(folder/'joint.json')
        assert result['passed'] and result['map_WRAM_VRAM_verified']==53
        assert result['firmware_SHA256']==release['firmware_SHA256'] and result['client_SHA256']==ref['cost']['client']
        for file in ('window.csv','obj-phases.json','packets.jsonl'):
            assert sha(folder/file)==sha(baseline/file)==ref['cost']['pins'][file]
        assert all(sha(folder/f'frame-{g}.rgb')==sha(baseline/f'frame-{g}.rgb') for g in range(905,958))
        assert result['ARM_instructions']==ref['cost']['instructions'] and result['wire_B']==ref['cost']['SPI_B']
        assert result['SysTick_calls']==ref['cost']['irqs'] and result['ROM_read_allocations']==ref['cost']['ROM_reads']
        assert not any((folder/n).exists() for n in ('map-error.txt','callback-error.txt'))
        e=defaultdict(list)
        for r in read(folder/'events.json'):e[r['generation']].append(r)
        c=csv_groups(folder/'window.csv');s=csv_groups(folder/'seal528.csv')
        records=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
        packets=[bytes.fromhex(row[2]) for row in records]
        arrivals=[row[1] for row in records]
        rows=[breakdown(g,e[g],c[g],s[g],packets,arrivals) for g in WARM]
        phases.append(dict(start=ref['start'],warm=summarize(rows),dense=summarize([r for r in rows if r['g'] in DENSE]),
                           frames=rows,trace_SHA256={n:sha(folder/n) for n in ('events.json','window.csv','seal528.csv','packets.jsonl')}))
    assert len(phases)==2 and packet_content(a.runs[0])==packet_content(a.runs[1])
    switches=[]
    for left,right in zip(*(p['frames'] for p in phases)):
        assert left['g']==right['g']
        if (left['decision']=='fresh516')==(right['decision']=='fresh516'):continue
        same_list=[(r['kind'],r['dst'],r['B']) for r in left['commands']]==[(r['kind'],r['dst'],r['B']) for r in right['commands']]
        switches.append(dict(g=left['g'],same_SEAL_list=same_list,
                             decisions=[left['decision'],right['decision']],
                             final_wait_ms=[left['ms']['final_blank_wait'],right['ms']['final_blank_wait']],
                             call_ms=[left['call_ms'],right['call_ms']]))
    interventions=[]
    for phase,folder in zip(phases,a.gates):
        proof=read(folder/'audit.json')
        assert proof['frames']==41 and proof['target']==945 and proof['frozen_arrivals']
        assert phase['frames'][945-907]['decision']==proof['original']['decision']
        b,c=proof['original'],proof['narrow']
        if phase['start']==3000000:
            assert b['idle_maps']==[2240] and not c['idle_maps']
            assert b['decision']=='borrow516' and c['decision']=='fresh516' and c['waits']==b['waits']+1
            assert sum(c['seal_dma'])-sum(b['seal_dma'])==64 and c['ACK']>b['ACK']
        else:
            assert not b['idle_maps'] and not c['idle_maps'] and b['seal_dma']==c['seal_dma']
            assert b['decision']==c['decision']=='fresh516' and b['waits']==c['waits']
        interventions.append(proof)
        # Full per-command evidence is useful at decision boundaries. Keep the
        # other warm frames small; every input and instruction trace is pinned.
        for r in phase['frames']:
            if r['g'] in (919,928,945,946,951,952,953,954,955):continue
            r.pop('commands')
            r.pop('pre_load_ms')
    return dict(measured_firmware=release['firmware_SHA256'],physical=dict(displays=calls,output_ms=physical,
                final_poll_quiet_ms=(poll[3]*2**32+poll[4])*1000/freq/calls),phases=phases,
                phase_switches=switches,controlled_gate=interventions)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',nargs=2,type=Path,required=True)
    p.add_argument('--baseline',nargs=2,type=Path,required=True)
    p.add_argument('--gates',nargs=2,type=Path,required=True)
    for name in ('budget','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',encoding='utf8',newline='\n')
