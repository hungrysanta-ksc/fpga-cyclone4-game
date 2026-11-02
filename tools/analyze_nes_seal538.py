# SPDX-License-Identifier: MIT
"""Compare bounded SEAL groups and mixed OBJ batches on the same two continuous timelines."""
import argparse
import bisect
from collections import Counter
import csv
import json
from pathlib import Path

from analyze_nes_dense519 import consumed_tiles
from analyze_nes_phase537 import Calendar, ROOT, contents, csv_groups, dense_frames, ms, one, read, sha, wire_plan
from analyze_nes_prefix523 import packet_trace, verified_visible_dma


def sealed_951(folder, cpu):
    with (folder/'seal528.csv').open() as f:
        seal=[{k:int(v) if k!='event' else v for k,v in r.items()} for r in csv.DictReader(f) if r['g']=='951']
    load=one(cpu,'load')
    final=one(cpu,'final212')
    credit=one(seal,'final_credit')
    latches=[r for r in seal if r['event']=='latch']
    assert len(latches)==1 or (not latches and credit['bytes']>=1568)
    latch=latches[0] if latches else credit
    reveal=one(cpu,'reveal')
    sizes=Counter()
    starts=[]
    raw=False
    raw_start=None
    raw_clocks=0
    for row in seal:
        if row['event']=='raw_enter':
            raw=True
            assert raw_start is None
            raw_start=row['clock']
        elif row['event']=='raw_done':
            if raw:
                raw_clocks+=row['clock']-raw_start
                raw_start=None
            raw=False
        elif row['event']=='dma' and row['clock']<final['clock']:
            assert row['port']==24
            kind='raw' if raw else 'map' if (row['src']&0x7000)==0x5000 else 'tile'
            sizes[kind]+=row['bytes']
            starts.append((kind,row['clock'],row['bytes']))
    ends=[r for r in cpu if r['event']=='ppu_last' and r['clock']<final['clock']]
    assert raw_start is None and len(starts)==len(ends) and len(starts)>0
    dma_clocks=Counter()
    for (kind,start,_),end in zip(starts,ends):
        assert start<end['clock']
        dma_clocks[kind]+=end['clock']-start
    # PPU vertical coordinate and horizontal master clock from the real latch read.
    # A 1364-clock scanline approximation can differ by four ticks on a short line.
    line,h=latch['line'],latch['h']
    assert 0<=h<1364
    return dict(head_line=load['line'],DMA_B=sizes,DMA_count=Counter(x[0] for x in starts),
                DMA_active_ms={k:ms(v) for k,v in dma_clocks.items()},raw_execution_clocks=raw_clocks,
                head_to_first_DMA_ms=ms(starts[0][1]-load['clock']),
                gate_sample='beam' if latches else 'credit',first_DMA_to_gate_ms=ms(latch['clock']-starts[0][1]),gate_line=line,gate_h=h,
                line246_margin_ms_approx=ms((247-line)*1364-h),blank_left_ms_approx=ms((262-line)*1364-h),
                credit=credit['bytes'],head_to_reveal_VB=reveal['frame']-load['frame'],
                final_waits=sum(r['event']=='wait169' and r['clock']>=final['clock'] for r in cpu))


def obj_952(events, obj, prev, cpu):
    relative=lambda clock:ms(clock-prev)
    enter=one(events,'end_enter')['clock']
    last=obj['obj_plans'][-1]['accepted_clock']
    e9=[r for r in events if r.get('opcode')=='0xe9']
    commit=e9[-1]
    assert obj['end_accepted']==commit['clock']
    status=Counter()
    for r in events:
        if r.get('opcode')=='0xe8' and enter <= r['start'] < commit['start']:
            reply=bytes.fromhex(r['reply'])
            status['bulk' if reply[6] else 'ready' if reply[3]&1 else 'busy']+=1
    ack=[r for r in cpu if r['op']==7 and r['section']==1 and r['event']=='ack']
    seal=[r for r in cpu if r['op']==3]
    return dict(E9_ms=[relative(r['clock']) for r in e9],OBJ_batch_sizes=list(Counter(p['accepted_clock'] for p in obj['obj_plans']).values()),
                END_entry_ms=relative(enter),last_OBJ_accept_ms=relative(last),END_accept_ms=relative(commit['clock']),
                END_pending_ms=ms(commit['start']-enter),E8_while_END_pending=status,
                first_OBJ_request_ms=relative(obj['first_obj_rom_request']),last_OBJ_response_ms=relative(obj['last_obj_rom_response']),
                last_OBJ_consumer_ACK_ms=relative(ack[-1]['clock']),SEAL_head_ms=relative(one(seal,'load')['clock']),
                OBJ_reads=obj['obj_rom_reads'])


def inspect_run(folder, plans, cal, base, expected_firmware, expected_client, *, omitted_raw_B=0, first_bg_limit=1):
    joint=read(folder/'joint.json')
    ref=read(base/'joint.json')
    assert joint['passed'] and joint['commits']==joint['map_WRAM_VRAM_verified']==53 and joint['last_status']==1
    assert joint['firmware_SHA256']==expected_firmware and joint['client_SHA256']==expected_client
    assert joint['parameters']==ref['parameters'] and joint['parameters']['ROM_calendar']==cal.summary
    assert omitted_raw_B>=0 and joint['vram_DMA_B']+omitted_raw_B==ref['vram_DMA_B']
    assert joint['ROM_read_allocations']==ref['ROM_read_allocations']
    assert joint['max_bulk_banks']<=2 and not any((folder/f).exists() for f in ('map-error.txt','callback-error.txt'))
    assert consumed_tiles(folder)==consumed_tiles(base)
    other,raw=contents(folder)
    other_ref,raw_ref=contents(base)
    assert raw==raw_ref and {k:v for k,v in other.items() if k[0][0]!=7}=={k:v for k,v in other_ref.items() if k[0][0]!=7}
    assert all(sha(folder/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,958))
    trace,packets,_,_=packet_trace(folder)
    visible=verified_visible_dma([r for r in trace if int(r['g'])>=905])
    cpu=csv_groups(folder/'window.csv')
    events=read(folder/'events.json')
    phases=read(folder/'obj-phases.json')
    waits={}
    for g in range(905,958):
        seal=[r for r in cpu[g] if r['op']==3]
        reveal,ack,final=[one(seal,k) for k in ('reveal','ack','final212')]
        assert reveal['frame']==ack['frame'] and reveal['line']>=225 and ack['value']==1
        assert ack['clock']==joint['frames'][g-905]['ACK_masterclock']
        waits[g]=sum(r['event']=='wait169' and r['clock']>=final['clock'] for r in seal)
    bg={}
    for g in range(905,958):
        qs=[bytes.fromhex(q) for _,q in read(plans/f'frame{g}/plans.json')]
        if not any(q[6]==0 for q in qs):
            continue
        assert [q[6] for q in qs[:2]]==[2,0]
        first=next(r for r in events if r['generation']==g and r.get('opcode')=='0xe9')
        assert 1<=first_bg_limit<=3
        allowed=[]
        for count in range(1,min(first_bg_limit,len(qs)-1)+1):
            if qs[count][6]!=0:
                break
            allowed.append(8+sum(len(wire_plan(q)) for q in qs[:count+1]))
        assert first['bytes'] in allowed
        request=first['clock']+75
        grant,response=cal.select(request)
        cycle,offset=divmod(request,cal.period)
        preceding=bisect.bisect_left(cal.starts,offset)-1
        prior_grant=(cycle-(preceding<0))*cal.period+cal.starts[preceding]
        if 'rom_service' in phases[str(g)]:
            actual=phases[str(g)]['rom_service'][0]
            assert actual[0]==0 and abs(actual[1]-request)<0.001 and actual[2:]==[grant,response]
        prev=(one([r for r in cpu[g-1] if r['op']==3],'reveal')['clock']
              if g>905 else joint['parameters']['start'])
        # Count periodic ROM frame windows relative to the previous displayed screen.
        source=one([r for r in events if r['generation']==g],'source_begin')['clock']
        bg[g]=dict(grant_clock=grant,grant_after_reveal_ms=ms(grant-prev),wait_ms=ms(grant-request),
                   input_after_reveal_ms=ms(source-prev),request_after_input_ms=ms(request-source),
                   previous_grant_to_request_ms=ms(request-prior_grant),
                   relative_window=int(grant*8//cal.period-prev*8//cal.period))
    dense=dense_frames(folder)
    return dict(dense_frames=dense,dense_VB=sum(v['before_head']+v['after_head'] for v in dense.values()),
                dense_ms=sum(v['display_ms'] for v in dense.values())/5,last_ACK=joint['frames'][-1]['ACK_masterclock'],
                waits={g:waits[g] for g in (952,954)},BG=bg,
                after_951=sealed_951(folder,[r for r in cpu[951] if r['op']==3]),
                before_952=obj_952([r for r in events if r['generation']==952],phases['952'],
                                   one([r for r in cpu[951] if r['op']==3],'reveal')['clock'],cpu[952]),
                visible_DMA=visible,SPI_B=joint['wire_B'],ARM_instructions=joint['ARM_instructions'],IRQ=joint['SysTick_calls'],
                ROM_reads=joint['ROM_read_allocations'],DMA_B=joint['vram_DMA_B'],packets=len(packets),
                pins={n:sha(folder/n) for n in ('joint.json','packets.jsonl','window.csv','seal528.csv','obj-phases.json','events.json')})


def analyze(a):
    cal=Calendar(a.calendar)
    old=read(ROOT/'analysis/frontier536-verification.json')
    phases=[]
    for i in (1,2):
        control=old['phases'][i-1]['base']
        base=a.traces/f'nes-frontier536-base{i}'
        assert all(sha(base/n)==value for n,value in control['pins'].items())
        phase={}
        for name in ('base','display','obj','both','inline'):
            d=base if name=='base' else a.traces/f'nes-seal538-{name}{i}'
            firmware=sha(a.arm/'obj-nes-100/firmware.stm') if name in ('obj','both') else control['firmware']
            client=sha(a.client/'sink165.sfc') if name in ('display','both') else control['client']
            if name=='inline':
                client=sha(a.inline_client/'sink165.sfc')
            plans=a.oracle if name in ('obj','both') else a.plans
            r=inspect_run(d,plans,cal,base,firmware,client)
            if name!='base':
                audit=a.traces/f'nes-seal538-audit-{name}{i}'
                r['replay']=read(audit/'audit.json')
                assert r['replay']['frames']==53 and r['replay']['trace']==sha(d/'window.csv')
                assert sha(audit/'tile532.csv')==sha(d/'tile532.csv')
            phase[name]=r
            r['last_ACK_delta_ms']=ms(r['last_ACK']-phase['base']['last_ACK'])
            r['later_BG_windows']=[g for g,x in r['BG'].items() if x['relative_window']>phase['base']['BG'][g]['relative_window']]
            r['BG_window_preserved']=not r['later_BG_windows']
            r['pass']=r['BG_window_preserved'] and not any(r['waits'].values()) and r['dense_ms']<phase['base']['dense_ms'] and r['last_ACK_delta_ms']<0
        phases.append(phase)
    guards=dict(ARM=read(a.arm.parent.parent/'armguards.json'),mixed=read(a.arm.parent.parent/'mixedguards.json'),
                priority=read(a.traces/'nes-seal538-priority/result.json'),
                sealed_STOP=read(a.stop/'result.json'),inline_priority=read(a.traces/'nes-seal538-ipriority/result.json'),
                inline_STOP=read(a.traces/'nes-seal538-istop/result.json'))
    assert len(guards['ARM']['first'])==9 and len(guards['ARM']['end'])==6 and len(guards['priority'])==22 and len(guards['sealed_STOP'])==4
    assert len(guards['inline_priority'])==22 and len(guards['inline_STOP'])==7
    build=read(a.client/'build.json')
    image=a.arm/'obj-nes-100/firmware.stm'
    return dict(phases=phases,guard=guards,build=dict(ARM_SHA256=sha(image),ARM_Flash_B=image.stat().st_size,
                ARM_BSS_B=int((a.arm.parent/'size.log').read_text().splitlines()[-1].split()[2]),
                client_SHA256=sha(a.client/'sink165.sfc'),body_B=build['body_bytes'],body_free_B=build['body_free']),
                inline_build=dict(client_SHA256=sha(a.inline_client/'sink165.sfc'),body_B=read(a.inline_client/'build.json')['body_bytes']),
                gate={n:all(p[n]['pass'] for p in phases) for n in ('display','obj','both','inline')})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','plans','oracle','calendar','arm','client','stop','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--inline-client',type=Path,required=True)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args),indent=2)+'\n',newline='\n')
