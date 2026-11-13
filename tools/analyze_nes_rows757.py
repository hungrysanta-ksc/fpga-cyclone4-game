# SPDX-License-Identifier: MIT
"""Correlate real ARM stores/slot ownership with SPI credit and 65816 VRAM and ACK."""
import argparse
import json
from pathlib import Path
from analyze_nes_window756 import summarize
from analyze_nes_map628 import normalize
from analyze_nes_owner739 import csv_groups,ms,read,sha


def ranges(folder,summary):
    stream=read(folder/'events.json')
    ev=[e for e in stream if e['generation']==957]
    begin=next(e['clock'] for e in ev if e['event']=='planner_enter')
    end=next(e['clock'] for e in ev if e['event']=='prepare_enter')
    deadline=summary['first248'][1]
    stamps={}
    image=bytearray((folder/'map-956.bin').read_bytes())
    final=(folder/'map-957.bin').read_bytes()
    stores={i:[] for i in range(2048,3584,192)}
    owned={}
    clock_of=lambda t:ms(t-deadline)
    for e in ev:
        if not begin<=e.get('clock',0)<=end:continue
        if e['event']=='slot_used757':
            for j in range(e['size']*8):
                slot=e['byte']*8+j
                if slot<1024 and e['value']&(1<<j):owned.setdefault(slot,e['clock'])
        if e['event']!='map_store757':continue
        old,new=map(bytes.fromhex,(e['old'],e['new']))
        at=e['offset']
        assert image[at:at+len(new)]==old and len(new)==len(old)
        image[at:at+len(new)]=new
        for word in range(at&~1,at+len(new),2):
            left=max(at,word)-at;right=min(at+len(new),word+2)-at
            stores[2048+(word-2048)//192*192].append((word,e['clock'],new[left:right]!=old[left:right]))
    assert image[2048:3584]==final[2048:3584]
    # Capture both the SNES consumption of this FIFO head and the subsequent
    # ARM credit receipt. The latter may cover several independently retired heads.
    credits=[e for e in stream if e['event']=='credit673']
    heads=[e for e in ev if e['event']=='wire664' and e['section']==2]
    cpu=csv_groups(folder/'window.csv')
    retired={r['index']:r['clock'] for generation in cpu.values() for r in generation if r['event']=='ack'}
    first_blank=summary['first248']
    for row in summary['page']:
        at=row['offset'];writes=stores[at]
        head,=[e for e in heads if e['offset']==at]
        seq=head['sent']+1
        assert row['retired']==retired[seq]
        def counter_time(counter):
            return next(e['clock'] for e in credits if e['before']<counter<=e['after'])
        slot_credit=counter_time(seq-4)
        observed=counter_time(seq)
        assert slot_credit<=row['start'] and observed>=row['retired']
        last_write=max(w[1] for w in writes)
        last_change=max((w[1] for w in writes if w[2]),default=None)
        # Inherited offscreen cells are copied verbatim and require no slot
        # decision for this generation. Check each touched word independently.
        cell_write={w[0]:w[1] for w in writes}
        slot_times={word:owned[int.from_bytes(final[word:word+2],'little')&1023] for word in cell_write}
        assert all(slot_times[word]<=stamp for word,stamp in cell_write.items())
        final_slot=max(slot_times.values())
        assert last_write<=row['start'] and final_slot<=last_write
        local_spi=[dict(op=e['opcode'],B=e['bytes'],end_ms=clock_of(e['clock'])) for e in ev if
                   e['event']=='SPI' and writes[0][1]<=e['clock']<=last_write]
        stamps[at]=dict(during_writes_SPI=local_spi,inherited_cells=96-len(cell_write),minimum_FIFO_retire=clock_of(retired[seq-4]),
            touched_cells=len({w[0] for w in writes}),last_write=clock_of(last_write),
            last_value_change=clock_of(last_change) if last_change else None,
            last_required_slot=clock_of(final_slot),four_slot_credit_available=clock_of(slot_credit),
            first_E1=clock_of(row['start']),CPU_accept=clock_of(row['accepted']),
            CPU_return=clock_of(row['retired']),ARM_return=clock_of(observed),
            before_BG_end=row['start']<next(e['clock'] for e in ev if e['event']=='bg_map_frozen'))
    # Zero-cost preparation and arbitration, real wire durations, FIFO order.
    # Never charge competing traffic or queue waits to this optimistic lower bound.
    wire_end=0
    change_end=0
    service_end=0
    payload_wire_end=float('-inf')
    for row in summary['page']:
        words=stores[row['offset']]
        ready=max(w[1] for w in words)
        span=row['push']-row['start']
        wire_end=max(wire_end,ready)+span
        changed=max((w[1] for w in words if w[2]),default=begin)
        change_end=max(change_end,changed)+span
        service_end=max(wire_end,service_end)+row['retired']-row['accepted']
        payload_wire_end=max(ms(ready-deadline),payload_wire_end)+row['B']*8/2625
    # For ordered transmissions the tightest release is the start of the
    # suffix with the latest possible finish. This also identifies which
    # production boundary has to move before increasing queue credit helps.
    suffix=0
    bounds={}
    for row in reversed(summary['page']):
        suffix+=row['B']*8/2625
        bounds[row['offset']]=stamps[row['offset']]['last_write']+suffix
    critical=max(bounds,key=bounds.get)
    assert abs(bounds[critical]-payload_wire_end)<1e-8
    return dict(critical_suffix_start=critical,reference='ms relative to end of first VBlank line 248',bounds=first_blank,as_measured_service_replay_ms=clock_of(service_end),
                wire_only_no_driver_ms=payload_wire_end,
                rows=stamps,last_E1_earliest_ms=clock_of(wire_end),last_E1_last_change_only_ms=clock_of(change_end))


def analyze(temp,probe):
    result={'phases':{},'selected':'753'}
    for n in (1,2):
        base=temp/f'nes-credit753-prefix{n}';work,_=normalize(base)
        phase=result['phases'][n]={}
        ref=summarize(base,base,n,work)
        for mode in ('control','row','pair','page'):
            d=temp/f'nes-rows757-{mode}{n}';v=summarize(d,base,n,work)
            detail=ranges(d,v)
            arm=probe.parent/'nes-credit753/arm-prefix' if mode=='control' else probe/f'arm-{mode}'
            firmware=arm/'src/obj-nes-100/firmware.stm'
            assert v['firmware']==sha(firmware)
            v.update(detail,Flash_B=firmware.stat().st_size,dense_delta_ms=v['mean_ms']-ref['mean_ms'],
                ACK_delta_ms=ms(v['ACK']-ref['ACK']),early_heads=sum(r['before_BG_end'] for r in detail['rows'].values()))
            if mode=='control':
                assert all(v[k]==ref[k] for k in ('page','ACK','intervals','mean_ms','map_DMA','BG','OBJ'))
            v['qualified']=(v['last_map_late_ms']<=0 and v['intervals'][957]==2 and v['safe_schedule']
                            and v['dense_delta_ms']<0 and v['ACK_delta_ms']<0 and v['Flash_B']<=212992)
            phase[mode]=v
    result['ARM_guards']={}
    for mode in ('row','pair','page'):
        guard=read(probe/f'guards-{mode}.json')
        assert all(guard['firmware']==v[mode]['firmware'] for v in result['phases'].values())
        assert guard['menu']['firmware']==guard['firmware']
        result['ARM_guards'][mode]=guard
        if all(p[mode]['qualified'] for p in result['phases'].values()):result['selected']=mode
    result['receiver_guards']={}
    for n in (1,2):
        result['receiver_guards'][n]={f:read(temp/f'nes-rows757-row{n}-{f}/verified751.json')
                                     for f in ('before','during','head','stale')}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+'\n',encoding='utf8',newline='\n')
