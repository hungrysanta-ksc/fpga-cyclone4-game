# SPDX-License-Identifier: MIT
"""Rebuild row receipts and canonical bytes independently of the producer and consuming ROM."""
import argparse
import csv
import json
import struct
from pathlib import Path
from statistics import mean
from analyze_nes_transfer512 import CLOCKS_PER_MS, equivalent_packets, fpga, logical_packets, read
from check_nes_game478 import Machine
from nes_raw506 import sha

def expand(d, capture):
    normalized=[]
    history=[0,0]
    published=[None,None]
    receipt=0
    partial=[]
    for b,tile in logical_packets(d):
        op,k,seq,serial,g,at,n,witness=struct.unpack_from('<BBHIHHHH',b)
        bank=(serial-1)&1
        if op==1:receipt=0
        if op==3:
            published[bank]=serial
            history[bank]=receipt
            if serial<=2:assert receipt==(1<<64)-1
        if k==2 and op in (2,11):
            lo,hi=at//64*64,(at+n+63)//64*64
            rows=sum(1<<r for r in range(lo//64,hi//64))
            assert not receipt&rows
            receipt|=rows
            if op==11:
                assert published[bank]==witness==serial-2 and n%8==at%8==0 and 0<n<hi-lo<=192
                old=(capture/f'frame{g-2}/expected-map.bin').read_bytes()
                new=(capture/f'frame{g}/expected-map.bin').read_bytes()
                for start,end in ((lo,at),(at+n,hi)):
                    if start==end:continue
                    assert history[bank]&(1<<(start//64))
                    assert old[start:end]==new[start:end]==bytes(end-start)
                assert new[at:at+n]==b[16:]
                partial.append((g,lo,hi-lo,n))
                b=bytes([2])+b[1:10]+lo.to_bytes(2,'little')+(hi-lo).to_bytes(2,'little')+bytes(2)+new[lo:hi]
        normalized.append((b,tile))
    return equivalent_packets(normalized),partial

def opportunity(trim_trace, capture):
    published=[0,0]
    total=zero=eligible=0
    for b,tile in logical_packets(trim_trace):
        op,k,_,serial,g,at,n,_=struct.unpack_from('<BBHIHHHH',b)
        bank=(serial-1)&1
        if op==1:received=0
        if op==3:published[bank]=received
        if k!=2 or op not in (2,10):continue
        lo,hi=at//64*64,(at+n+63)//64*64
        received|=sum(1<<r for r in range(lo//64,hi//64))
        if op!=10:continue
        data=(capture/f'frame{g}/expected-map.bin').read_bytes()
        total+=hi-lo-n
        for group in (range(lo,at,8),range(hi-8,at+n-1,-8)):
            for offset in group:
                if data[offset:offset+8]!=bytes(8):break
                zero+=8
                if published[bank]&(1<<(offset//64)):eligible+=8
    return dict(unchanged_edge_B=total,zero_outer_edge_B=zero,with_prior_row_receipt_B=eligible)

def commit_cost(src, trace):
    m=Machine(src,bytes(128))
    layout=m.layout['nes_resident211']
    def field(name,value,n):
        m.u.mem_write(m.resident+layout[name],value.to_bytes(n,'little'))
    rows=bytearray(64)
    costs=[]
    for b,tile in logical_packets(trace):
        op,k,_,serial,g,at,n,_=struct.unpack_from('<BBHIHHHH',b)
        if op==1:rows=bytearray(64)
        if k==2 and op in (2,11):
            lo,hi=at//64,(at+n+63)//64
            rows[lo:hi]=bytes([255])*(hi-lo)
        if op!=3:continue
        bank=(serial-1)&1
        for name,value,size in [('open',1,1),('prepared',1,1),('serial',serial,4),('target',bank,1),('generation',g,2)]:
            field(name,value,size)
        if 'map_groups' in layout:
            m.u.mem_write(m.resident+layout['map_groups']+bank*64,bytes(rows))
        before=m.instructions
        assert m.call('nes_resident211_commit',[m.resident,serial,g,bank,1])==1
        costs.append(m.instructions-before)
    assert len(costs)==12
    return costs

def phase_comparison(t,reference,capture):
    scenarios={}
    for label in ('original','control','history'):
        folder=t/f'nes-history515-phase-{label}01'
        j=read(folder/'joint.json')
        spec=dict(reference['parameters'],start=3178684)
        assert j['passed'] and j['commits']==12 and j['parameters']==spec
        assert j['map_WRAM_VRAM_verified']==12 and j['future_ACK_filtered'] and j['max_bulk_banks']<=2
        assert j['last_status']==1 and j['ROM_read_allocations']==3280
        source=t/({'original':'nes-transfer512-original04','control':'nes-trim514-control-joint01','history':'nes-history515-joint02'}[label])
        assert j['firmware_SHA256']==read(source/'joint.json')['firmware_SHA256']
        for g in range(905,917):
            assert sha(folder/f'frame-{g}.rgb')==sha(source/f'frame-{g}.rgb')
        canonical,_=expand(folder,capture)
        assert canonical==equivalent_packets(logical_packets(t/'nes-transfer512-original04'))
        times=[f['ACK_masterclock'] for f in j['frames']]
        intervals=[(b-a)/CLOCKS_PER_MS for a,b in zip(times[1:],times[2:])]
        scenarios[label]=dict(first_ms=(times[0]-spec['start'])/CLOCKS_PER_MS,
                              later_mean_ms=mean(intervals),later_intervals_ms=intervals,
                              final_ACK_masterclocks=times,wire_B=sum(j['wire_B'].values()),
                              IRQ=j['SysTick_calls'],joint_SHA256=sha(folder/'joint.json'))
    return dict(start=3178684,shift_masterclocks=178684,runs=scenarios)

def check(a):
    t=a.temp
    base=t/'nes-transfer512-original04'
    ctrl=t/'nes-trim514-control-joint01'
    d=t/'nes-history515-joint02'
    j=read(d/'joint.json')
    prev=read(a.reference)
    assert j['passed'] and j['parameters']==prev['parameters'] and j['commits']==12
    assert j['last_status']==1 and j['future_ACK_filtered'] and j['max_bulk_banks']<=2 and j['map_WRAM_VRAM_verified']==12
    assert j['ROM_read_allocations']==3280
    expanded,partial=expand(d,a.capture)
    assert expanded==equivalent_packets(logical_packets(base))
    ev=read(d/'events.json')
    assert sum(e.get('opcode')=='0xea' for e in ev)==12
    for g in range(905,917):
        assert sha(d/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb')
        actual=[e['bytes'] for e in ev if e.get('opcode')=='0xd1' and e['generation']==g]
        rtl=(t/'nes-transfer512-spilegacy01'/f'transactions-{g}.txt').read_text().splitlines()
        assert actual==[int(l.split()[0]) for l in rtl if l.split()[1].startswith('d1')]
    times=[f['ACK_masterclock'] for f in j['frames']]
    intervals=[(b-a)/CLOCKS_PER_MS for a,b in zip(times,times[1:])]
    baseline=prev['runs']['original'];control=prev['runs']['control']
    assert sha(base/'joint.json')==baseline['joint_SHA256'] and sha(ctrl/'joint.json')==control['joint_SHA256']
    fw=a.probe/'ARM02'
    blob=fw/'src/obj-nes-100/firmware.stm'
    assert sha(blob)==j['firmware_SHA256']
    board=fpga(t/'nes-history515-fit03')
    assert sha(a.probe/'design03/client/sink-program.hex')==board['report_SHA256']['sink-program.hex']
    inputs=read(t/'nes-fault507-board01/source-pins.json')['board_inputs']
    assert [k for k,v in inputs.items() if sha(t/'nes-history515-fit03'/k)!=v]==['sink-program.hex']
    omitted=sum(n-m for _,_,n,m in partial)
    opportunity_B=opportunity(t/'nes-trim514-joint01',a.capture)
    assert opportunity_B['with_prior_row_receipt_B']==omitted
    assert j['vram_DMA_B']==baseline['VRAM_DMA_B']-omitted and j['wire_B']['0xe1']==baseline['E1_B']-omitted
    def costs(path):
        with path.open() as f:
            return {(int(r['generation']),int(r['offset'])//64*64):int(r['clocks']) for r in csv.DictReader(f)
                    if int(r['section'])==2 and int(r['op']) in (2,4,10,11)}
    original_cost=costs(t/'nes-trim514-cost01/original/service.csv')
    crc_cost=costs(t/'nes-trim514-cost01/trim/service.csv')
    new_cost=costs(t/'nes-history515-consume01/service.csv')
    def partial_ms(cost):return sum(cost[g,lo] for g,lo,_,_ in partial)/CLOCKS_PER_MS
    with (t/'nes-history515-consume01/publication.csv').open() as f:pub=list(csv.DictReader(f))
    assert [int(r['generation']) for r in pub]==list(range(905,917))
    guards=read(t/'nes-history515-guards03/guards.json')
    assert len(guards)==15 and all(r['passed'] for r in guards.values())
    arm=read(a.probe/'history02.json')
    assert arm['publication_checked'] and arm['firmware_SHA256']==sha(blob)
    stop_cost={}
    for mode in ('stop_check','stop_final'):
        cost=(t/'nes-history515-guards03'/mode/'stop-clocks.txt').read_text().split()
        invalid,total=map(int,cost);assert 0<invalid<=total
        stop_cost[mode]=dict(invalidate_masterclocks=invalid,stop_read_to_cancel_ACK_masterclocks=total)
    recover={}
    for fault in ('none','program','done','busy','token'):
        r=read(a.probe/f'recovery02-{fault}/result.json')
        assert r['passed'] and r['firmware_sha256']==sha(blob)
        recover[fault]=[r['safe_return'],r['base_restored']]
    q=read(t/'nes-history515-queue01/result.json')
    assert q['passed'] and q['partial']==len(partial) and q['trace_SHA256']==sha(d/'packets.jsonl')
    assert q['RTL_SHA256']==sha(t/'nes-history515-fit03/nes_sink_spi165.sv')
    size=(fw/'size.log').read_text().splitlines()[-1].split()
    v=dict(first_ms=(times[0]-j['parameters']['start'])/CLOCKS_PER_MS,second_ms=intervals[0],later_mean_ms=mean(intervals[1:]),
           later_min_ms=min(intervals[1:]),later_max_ms=max(intervals[1:]),later10_ms=sum(intervals[1:]),later_intervals_ms=intervals[1:],
           E1_B=j['wire_B']['0xe1'],E0_queries=j['wire_B']['0xe0']//20,wire_B=sum(j['wire_B'].values()),wire_by_op=j['wire_B'],
           VRAM_DMA_B=j['vram_DMA_B'],omitted_B=omitted,partial_records=len(partial),IRQ=j['SysTick_calls'],ARM_instructions=j['ARM_instructions'],
           ROM_reads=j['ROM_read_allocations'],firmware_B=blob.stat().st_size,Flash_free_B=0x34000-blob.stat().st_size,
           data_B=int(size[1]),BSS_B=int(size[2]),workspace_end=j['workspace_end'],observed_stack_low=j['observed_stack_low'],
           stack_gap_B=int(j['observed_stack_low'],16)-int(j['workspace_end'],16),SNES_body_B=read(a.probe/'design03/client/build.json')['body_bytes'],
           SNES_stack_B=j['observed_stack_B'],SNES_extra_WRAM_vs509_B=44,firmware_SHA256=sha(blob),joint_SHA256=sha(d/'joint.json'),
           trace_SHA256=sha(d/'packets.jsonl'),events_SHA256=sha(d/'events.json'))
    return dict(scope='12 fixed SMB3 captures; actual linked ARM/65816, SPI/IRQ/ROM calendar model. No new physical run.',
                alternate_start=phase_comparison(t,j,a.capture),parameters=j['parameters'],original=baseline,control=control,history515=v,FPGA=board,
                opportunity_B=opportunity_B,partial_original_ms=partial_ms(original_cost),partial_CRC514_ms=partial_ms(crc_cost),partial_history515_ms=partial_ms(new_cost),
                post_ACK_publication=pub,ARM_commit_instructions_original=commit_cost(a.probe.parent/'nes-service509/ARM03/src',base),
                ARM_commit_instructions_515=commit_cost(fw/'src',d),guards={k:[r['commits'],r['last_status']] for k,r in guards.items()},
                stop_cost=stop_cost,ARM_history=arm,base_recovery=recover,E1_RTL=q,RGB_equal=12,cold_banks_restored=2)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('temp','probe','capture','reference','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=check(a);a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
