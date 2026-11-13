# SPDX-License-Identifier: MIT
"""Match 53 logical outputs, then measure E1/CPU return, map DMA and the last display."""
import argparse
import json
from pathlib import Path

from analyze_nes_bg750 import counters
from analyze_nes_front755 import deadline
from analyze_nes_map628 import normalize
from analyze_nes_owner739 import csv_groups, ms, packets, read, sha


def summarize(folder, base, phase, reference, *, ordered_page=True):
    run=read(folder/'joint.json')
    assert run['passed'] and run['commits']==run['map_WRAM_VRAM_verified']==53
    assert run['parameters']==read(base/'joint.json')['parameters'] and run['max_bulk_banks']<=2
    work, counts=normalize(folder)
    assert work==reference
    for generation in range(905,958):
        for name in (f'frame-{generation}.rgb',f'map-{generation}.bin'):
            assert sha(folder/name)==sha(base/name)
    cpu=csv_groups(folder/'window.csv')
    def event(gen,name):
        return next(r for r in cpu[gen] if r['event']==name and r['op']==3)
    prev,shown=event(956,'reveal'),event(957,'reveal')
    start=event(956,'ack')['clock']
    lo,hi=deadline(folder,prev)
    ev=[e for e in read(folder/'events.json') if e['generation']==957]
    def clock(kind):
        return next(e['clock'] for e in ev if e['event']==kind)
    bg,prepared=clock('bg_map_frozen'),clock('prepare_enter')
    pushes=[e for e in ev if e.get('opcode')=='0xe1']
    loads=[r for r in cpu[957] if r['event']=='load']
    acks=[r for r in cpu[957] if r['event']=='ack']
    page=[]
    for (h,_,push),wire,load,ack in zip(packets(folder)[957], pushes, loads, acks, strict=True):
        offset=int.from_bytes(h[10:12],'little')
        if h[1]!=2 or not 2048<=offset<3584:continue
        assert abs(push-wire['clock'])<=1 and push<=load['clock']<=ack['clock']
        page.append(dict(offset=offset,op=h[0],B=wire['bytes'],start=wire['start'],push=push,
                         accepted=load['clock'],retired=ack['clock']))
    offsets=[r['offset'] for r in page]
    assert (offsets if ordered_page else sorted(offsets))==list(range(2048,3584,192))
    last=page[-1]['retired']
    assert last<lo or last>hi
    prior=read(Path('analysis/obj749-verification.json'))['phases'][str(phase)]['page']
    e8=next(e for e in ev if e.get('opcode')=='0xe8' and e['reply']==prior['E8_reply'])
    old=next(e for e in read(folder.parent/f'nes-obj749-page{phase}'/'events.json')
             if e.get('opcode')=='0xe8' and e.get('generation')==957 and e['reply']==prior['E8_reply'])
    dma=counters(folder/'dma748.csv')
    def transfer(r):
        rows=cpu[r['g']]
        idx=next(i for i,e in enumerate(rows) if e['event']=='ppu_dma' and e['clock']>=r['clock'])
        first=rows[idx];end=next(e for e in rows[idx+1:] if e['event']=='ppu_last')
        assert first['clock']-r['clock']<120 and first['value']==r['bytes']
        assert first['frame']==end['frame'] and 225<=r['line']<=end['line']<=261
        return dict(**r,frame=first['frame'],end=end['clock'],end_line=end['line'])
    maps={}
    for g,src in [(952,0xd800),(957,0x5800)]:
        maps[g]=[transfer(r) for r in dma if r['g']==g and src<=r['source']<src+1536
                 and r['clock']<event(g,'load')['clock']]
    obj,=[transfer(r) for r in dma if r['g']==957 and r['source']==19104 and r['bytes']==288]
    bg_dma,=[transfer(r) for r in dma if r['g']==957 and r['source']==0x840 and r['bytes']==48]
    first=maps[957][0] if maps[957] else None
    long=all([r['bytes'] for r in m]==[1536] for m in maps.values())
    ordered=bool(long and bg_dma['end']<first['clock']<first['end']<obj['clock'] and first['frame']==obj['frame'])
    intervals={g:event(g,'reveal')['frame']-event(g-1,'reveal')['frame'] for g in [908,911,*range(951,958)]}
    final=event(957,'final212')['clock']
    final_wait=sum(r['event']=='wait169' and r['clock']>final for r in cpu[957])
    masks=[r for r in counts[957]['deltas'] if 2048<=r['offset']<3584]
    if masks:assert [r['changed'] for r in masks]==[3,5,5,3,3,5,6,4]
    safe=bool(long and ordered and obj['line']<=256 and e8['clock']<=old['clock']
              and e8['start']<=old['start'] and intervals[908]<=2 and intervals[911]<=2
              and intervals[952]<=3 and event(951,'reveal')['line']<=246 and final_wait==0)
    entry=next(e['clock'] for e in ev if e['event']=='map_packet_enter' and e['offset']==2048)
    attempts=[e['outstanding'] for e in ev if e['event']=='map_credit_attempt' and bg<=e['clock']<prepared]
    immutable=next(e for e in ev if e['event']=='bg684_enter' and e['final']==1
                   and e['map_sha']==sha(folder/'map-957.bin'))
    page_snapshots=[e for e in ev if e['event']=='bg684_enter' and e.get('final')==2 and bg<=e['clock']<prepared]
    return dict(OBJ_offer_count=len(page_snapshots), final_BG_callback_late_first248_ms=ms(immutable['clock']-hi),
          last_map_write_late_first248_ms=ms(immutable['last_map_write']-hi),OBJ_attempt_credits=attempts,
          BG_freeze_late_first248_ms=ms(bg-hi),OBJ_end_late_first248_ms=ms(prepared-hi),
          BG_freeze_to_first_page_entry_ms=ms(entry-bg),
          SPI_957_B=sum(e['bytes'] for e in ev if 'opcode' in e and 'bytes' in e),
          page=page,changed_groups=masks,bank=counts[957]['bank'],
          BG_freeze_to_first_page_wire_ms=ms(page[0]['start']-bg),
          BG_freeze_to_OBJ_prepared_ms=ms(prepared-bg),issued_during_OBJ=sum(bg<=r['start']<prepared for r in page),
          last_page_after_956_ACK_ms=ms(page[-1]['push']-start),page_SPI_B=sum(r['B'] for r in page),page_SPI_ms=sum(ms(r['push']-r['start']) for r in page),
          page_head_to_ACK_ms=sum(ms(r['retired']-r['accepted']) for r in page),
          last_map_after_956_ACK_ms=ms(last-start),first248=[lo,hi],last_map_late_ms=ms(last-hi),
          map_DMA=maps,OBJ=obj,BG=bg_dma,E8_delta749_clocks=e8['start']-old['start'],
          SEAL_after_956_ACK_ms=ms(event(957,'load')['clock']-start),same_blank_ordered=ordered,
          safe_schedule=safe,final_wait957=final_wait,intervals=intervals,public951=event(951,'reveal')['line'],
          mean_ms=ms(shown['clock']-event(951,'reveal')['clock'])/6,ACK=event(957,'ack')['clock'],
          SPI_B=sum(run['wire_B'].values()),stack_gap_B=int(run['observed_stack_low'],16)-int(run['workspace_end'],16),
          firmware=run['firmware_SHA256'],ROM=run['client_SHA256'],pins={n:sha(folder/n) for n in
          ('events.json','packets.jsonl','window.csv','dma748.csv','joint.json')})


def analyze(temp,probe):
    result=dict(phases={},selected='753')
    for n in (1,2):
        base=temp/f'nes-credit753-prefix{n}'
        logical,_=normalize(base)
        rows=result['phases'][n]={}
        for k in ('753','control','overlap','refresh','deltapage','bothpage'):
            d=base if k=='753' else temp/f'nes-window756-{k}{n}'
            r=summarize(d,base,n,logical)
            image=(probe.parent/'nes-credit753/arm-prefix' if k in ('753','control') else probe/f'arm-{k}')/'src/obj-nes-100/firmware.stm'
            assert sha(image)==r['firmware']
            r['Flash_B']=image.stat().st_size
            r['BSS_B']=int((image.parents[2]/'size.log').read_text().splitlines()[-1].split()[2])
            rows[k]=r
            ref=rows['753']
            r['dense_delta_ms']=r['mean_ms']-ref['mean_ms']
            r['ACK_delta_ms']=ms(r['ACK']-ref['ACK'])
            if k=='control':
                assert all(r[key]==ref[key] for key in ('intervals','mean_ms','ACK','page','map_DMA','OBJ','first248'))
            if k in ('bothpage','deltapage'):
                assert len(r['changed_groups'])==8
    result['ARM_guards']={}
    for k in ('overlap','refresh','deltapage','bothpage'):
        guard=read(probe/f'guards-{k}.json')
        assert guard['firmware']==result['phases'][1][k]['firmware']==guard['menu']['firmware']
        result['ARM_guards'][k]=guard
    result['rejected_wide_history']={}
    for k in ('delta','both'):
        records=[]
        for n in (1,2):
            log=temp/f'nes-window756-{k}{n}.log'
            assert "('ARM stack overlap', '0x2000f8b8', '0x2000f8c0')" in log.read_text(encoding='utf8')
            records.append(sha(log))
        result['rejected_wide_history'][k]=dict(capacity_per_bank=880,overlap_B=8,log_hashes=records)
    result['faults']={}
    for k in ('identity','checksum','retained','partial'):
        d=temp/('nes-window756-guard-'+k+'1'+('-restart' if k=='partial' else ''))
        result['faults'][k]=read(d/'verified756.json')
        if k=='partial':
            result['cold_restart']=read(d/'restart/audit.json')
            assert result['cold_restart']['frames']==2 and (d/'stopped-maps.bin').stat().st_size==16384
    result['new_head']={n:read(temp/f'nes-window756-guard-head{n}/verified751.json') for n in (1,2)}
    result['ideal_earlier_offers']={}
    for n in (1,2):
        a=read(temp/f'nes-window756-ideal{n}/audit711.json')
        assert a['passed'] and a['same_pixels'] and a['advance_us']==3570
        result['ideal_earlier_offers'][n]=dict(interval=a['metrics']['957']['interval_VBlank'],
            ACK_delta_ms=ms(a['last_ACK']-result['phases'][n]['753']['ACK']),
            SEAL_advance_ms=a['metrics']['957']['seal_load_advance_ms'])
    result['ROM']=read(probe/'client/build.json')
    result['qualified']=[k for k in ('overlap','refresh','deltapage','bothpage') if
        all(row[k]['safe_schedule'] and row[k]['intervals'][957]==2 and row[k]['last_map_late_ms']<=0
            and row[k]['dense_delta_ms']<0 and row[k]['ACK_delta_ms']<0 and row[k]['Flash_B']<=212992
            for row in result['phases'].values()) and (k in ('overlap','refresh') or result['ROM']['board_fit'])]
    if result['qualified']:result['selected']=result['qualified'][0]
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('temp','probe','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.probe),indent=2)+'\n',encoding='utf8',newline='\n')
