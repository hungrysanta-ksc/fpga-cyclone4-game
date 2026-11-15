# SPDX-License-Identifier: MIT
"""Attribute 969 E8 latency to an immutable bank, its reader and SPI sampling."""
import argparse
import json
from pathlib import Path

from analyze_nes_output768 import csv_groups, one, read, sha, timeline
from test_nes_banks557 import host_after
from test_nes_raw506_joint import MASTER


def ms(ticks):
    return ticks*1000/MASTER


def head_trace(folder, circuit):
    cpu=csv_groups(folder/'window.csv')
    previous=one([r for r in cpu[968] if r['op']==3],'ack')['clock']
    assert circuit['previous']==previous
    events=[e for e in read(folder/'events.json') if e['generation']==969]
    queries=[]
    for e in events:
        if e.get('opcode')=='0xe8':
            d=bytes.fromhex(e['reply'])
            if d[6]:
                token=int.from_bytes(d[14:18],'little')
                queries.append((token,e))
    prior=next(e for token,e in queries if token==160)
    final=next(e for token,e in queries if token==161)
    issue=next(e for e in events if e.get('packet_opcode')==7 and e['start']>=prior['clock'])
    phase=read(folder/'obj-phases.json')['969']
    origin=circuit['origin']
    close,head,strobe=circuit['RTL_ns']
    head=origin+head*MASTER/1e9
    last_rom=phase['last_obj_rom_response']
    terms=dict(ROM_complete=last_rom,sealed=origin+close*MASTER/1e9,
               previous_OBJ_E8_start=prior['start'],previous_OBJ_E1_start=issue['start'],
               previous_OBJ_consume=circuit['releases'][2],head=head,
               last_E8_start=final['start'],last_E8_sample=host_after(final['start']+7.5*MASTER/2625000,3),
               last_E8_end=final['clock'])
    assert last_rom<terms['sealed']<head<terms['last_E8_sample']<final['clock']
    assert abs(terms['sealed']-circuit['END_check'])<10
    assert set(phase['cache611'][i][-1] for i in range(32))=={'OBJ_capture'}
    bit=next((e for e in events if e.get('opcode')=='0xe0' and
              terms['sealed']<e['start']<prior['start'] and bytes.fromhex(e['reply'])[2]&8),None)
    if bit:terms['map_progress_E0']=bit['clock']
    return dict(from_968_ACK_ms={k:round(ms(t-previous),6) for k,t in terms.items()},
                head_to_E8_end_ms=round(ms(final['clock']-head),6),
                sealed_until_head_ms=round(ms(head-terms['sealed']),6),
                end_check_offset_masterclocks=round(terms['sealed']-circuit['END_check'],5),
                RTL_consume_stimulus_to_head_ns=round(circuit['RTL_ns'][1]-strobe),
                source_hashes={f:sha(folder/f) for f in ('obj-phases.json','events.json','window.csv','packets.jsonl')})


def schedule(folder,ref):
    j=read(folder/'joint.json')
    assert j['passed'] and j['commits']==j['map_WRAM_VRAM_verified']==66
    for gen in range(905,971):
        for name in (f'frame-{gen}.rgb',f'map-{gen}.bin',f'expected-{gen}.bin'):
            assert (folder/name).read_bytes()==(ref/name).read_bytes(),(folder,name)
    cpu=csv_groups(folder/'window.csv')
    ev=read(folder/'events.json')
    packets=[json.loads(s) for s in (folder/'packets.jsonl').read_text().splitlines()]
    result=timeline(folder,969,cpu,ev,packets)
    def mark(g,event):
        return one([r for r in cpu[g] if r['op']==3],event)['clock']
    def interval(g):
        return ms(mark(g,'reveal')-mark(g-1,'reveal'))
    observe={}
    for token in (160,161):
        match=next(e for e in ev if e['generation']==969 and e.get('opcode')=='0xe8'
                   and bytes.fromhex(e['reply'])[6] and int.from_bytes(bytes.fromhex(e['reply'])[14:18],'little')==token)
        tx=next(e for e in ev if e['generation']==969 and e.get('packet_opcode')==7 and e['start']>=match['clock'])
        header=bytes.fromhex(next(h for _,t,h,_ in packets if abs(t-tx['clock'])<=1))
        assert int.from_bytes(header[16:20],'little')==token
        observe[token]=[round(ms(t-mark(968,'ack')),6) for t in (match['start'],tx['start'])]
    start=one([e for e in ev if e['generation']==969],'output_enter531')['clock']
    seal=one([r for r in cpu[969] if r['op']==3],'load')['clock']
    pre=[r for r in cpu[969] if r['event']=='ppu_dma' and start<r['clock']<seal]
    tail=None
    if result['dma_bytes_output_entry_to_SEAL_load']==496:
        assert [r['value'] for r in pre]==[192,16,192,32,64]
        assert pre[0]['frame']==pre[-1]['frame']
        spi=[e for e in ev if e['generation']==969 and e.get('opcode')=='0xe1' and e['start']>=pre[0]['clock']]
        wire=sum(e['bytes'] for e in spi)
        # Give the current line its entire duration. This overestimates the time
        # available to the original order, even before the stricter display gate.
        ticks_left=(262-pre[0]['line'])*1364
        tail=dict(line=pre[0]['line'],transactions=len(spi),wire_B=wire,wire_only_ms=round(8*wire/2625,6),
                  max_to_frame_end_ms=round(ms(ticks_left),6),
                  min_wire_overflow_ms=round(8*wire/2625-ms(ticks_left),6))
    return dict(remaining_E1_after_first_pre_DMA=tail,work=result['work'],start=j['parameters']['start'],pre_DMA_B=result['dma_bytes_output_entry_to_SEAL_load'],
                post_DMA_B=result['post_SEAL_DMA_bytes'],interval969_VB=result['display_interval_VB'],
                mean952_957_ms=round(sum(interval(g) for g in range(952,958))/6,6),
                intervals952_957_ms=[round(interval(g),6) for g in range(952,958)],
                ACK957=mark(957,'ack'),ACK969=mark(969,'ack'),ACK970=mark(970,'ack'),
                interval969_ms=round(interval(969),6),preseal_output_ms=result['before_SEAL_ms'],
                last_OBJ_E8_and_E1_ms=observe,frames_verified=j['commits'],client=j['client_SHA256'],
                firmware=j['firmware_SHA256'],parameters=j['parameters'],joint_sha256=sha(folder/'joint.json'))


def run(t,work):
    rtl=read(t/'nes-owner776-rtl04/result.json')
    output=dict(rtl=rtl,phase={})
    for ph in (1,2):
        phases=output['phase'][ph]={}
        ref=t/f'nes-cost768-763-p{ph}-ext'
        folders={'763':ref,'767':t/f'nes-cost768-767-p{ph}-ext',
                 '776':t/f'nes-owner776-joint-p{ph}','776B':t/f'nes-owner776-receipt-p{ph}',
                 'isolated':t/f'nes-owner776-isolated-p{ph}'}
        for v, folder in folders.items():
            row=phases[v]=schedule(folder,ref)
            assert row['start']==7288416+(ph-1)*178684
            if v in ('763','767'):
                row['owner']=head_trace(folder,rtl['cases'][f'{v}-p{ph}'])
            elif v=='isolated':
                old=read(folders['767']/'joint.json')['frames']
                new=read(folder/'joint.json')['frames']
                assert new[:-2]==old[:-2]
                assert row['client']==phases['767']['client'] and row['firmware']==phases['767']['firmware']
                hits=[e for e in read(folder/'events.json') if e['event']=='checked_receipt776']
                assert len(hits)==1 and hits[0]['generation']==969
                row['checked_receipt_clock']=hits[0]['clock']
            else:
                assert row['client']==phases['767']['client']
                arm='arm01' if v=='776' else 'arm02'
                assert row['firmware']==sha(work/arm/'src/obj-nes-100/firmware.stm')
            assert row['parameters']==phases['763']['parameters'] and row['work']==phases['763']['work']
        a,b=phases['763'],phases['767']
        assert b['pre_DMA_B']==496
        for name in ('776','776B','isolated'):
            row=phases[name]
            row['change_from_767']={
                'pre_DMA_B':row['pre_DMA_B']-b['pre_DMA_B'],
                'mean952_957_ms':round(row['mean952_957_ms']-b['mean952_957_ms'],6),
                'ACK969_masterclocks':row['ACK969']-b['ACK969'],
                'ACK970_masterclocks':row['ACK970']-b['ACK970'],
            }
        for row in (a,b):
            cost=row['owner']['from_968_ACK_ms']
            assert abs(cost['last_E8_end']-(cost['head']+row['owner']['head_to_E8_end_ms']))<2e-6
    assert rtl['stop_at_two_sealed']
    output['candidate_guards']=read(work/'snapshot-guards.json')
    output['receipt_guards']=read(work/'guards.json')
    output['receipt_B_guards']=read(work/'receiptB-guards.json')
    output['immediate_query_guards']=read(work/'immediate-guards.json')
    output['firmware_B']={arm:(work/arm/'src/obj-nes-100/firmware.stm').stat().st_size for arm in ('arm01','arm02')}
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('temp','work','out'):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.temp,a.work),indent=2)+'\n',encoding='utf8')
