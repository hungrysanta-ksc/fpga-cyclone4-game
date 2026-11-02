# SPDX-License-Identifier: MIT
"""Reconcile the same 18 immutable outputs with both coupled timelines."""
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path

from analyze_nes_map553 import map_times
from analyze_nes_phase537 import ROOT,Calendar,csv_groups,ms,one,read,sha
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare
from analyze_nes_upload550 import last_frame


def packet_schedule(folder,cal):
    events=[r for r in read(folder/'events.json') if r['generation']==954]
    cpu=csv_groups(folder/'window.csv')
    prev=one([r for r in cpu[953] if r['op']==3],'reveal')
    rel=lambda t:round(ms(t-prev['clock']),6)
    frozen=one(events,'immutable554')
    assert all(frozen['matches_capture'].values()) and len(frozen['last_writes'])==6
    prepare=one(events,'prepare_enter')['clock']
    assert frozen['clock']==prepare and max(frozen['last_writes'].values())<=prepare
    phase=read(folder/'obj-phases.json')['954']
    end=phase['end_accepted']
    final_reads=[x for x in phase['rom_service'] if x[1]>=end]
    assert len(final_reads)==18
    grants=Counter(int(x[2]*8//cal.period-prev['clock']*8//cal.period) for x in final_reads)
    last=max(r['clock'] for r in cpu[954] if r['event']=='ack' and r['op']==7)
    head=one([r for r in cpu[954] if r['op']==3],'load')
    reveal=one([r for r in cpu[954] if r['op']==3],'reveal')
    waits=[r for r in cpu[954] if r['op']==3 and r['event']=='wait169']
    final=one([r for r in cpu[954] if r['op']==3],'final212')['clock']
    commands=[r['value'] for r in cpu[954] if r['op']==3 and r['event']=='ppu_dma' and r['clock']<final]
    beam=[dict(event=r['event'],line=r['line'],h=r['h'],credit=r['bytes'] if r['event']=='final_credit' else None)
          for r in csv_groups(folder/'seal528.csv')[954] if r['event'] in ('final_credit','latch') and r['clock']>=final]
    ready=[r for r in events if r['event']=='ready554']
    wire=[r for r in events if r['event']=='wire554']
    spi=[r for r in events if r.get('opcode')=='0xe1']
    records=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    pushes=[r[1] for r in records]
    retired=sorted(r['clock'] for group in cpu.values() for r in group if r['event']=='ack')
    pending=[]
    for idx,(_,push,h,_) in enumerate(records,1):
        b=bytes.fromhex(h)
        op,sec=b[:2]
        if int.from_bytes(b[8:10],'little')!=954 or (sec not in (3,4,5) and op!=3):continue
        pending.append((idx,push,b))
    assert len(pending)==len(ready)==len(wire)==18
    rows=[]
    for (idx,push,b),r,w in zip(pending,ready,wire):
        seq=int.from_bytes(b[2:4],'little')
        at=int.from_bytes(b[10:12],'little')
        n=int.from_bytes(b[12:14],'little')
        expanded=int.from_bytes(b[14:16],'little')
        assert w['sequence']==seq and w['digest']==hashlib.sha256(b).hexdigest()
        assert r['section']==b[1] and r['offset']==at
        payload=bytes.fromhex(r['payload'])
        if b[0]==4 and r['op']==2:
            assert n==2 and payload==b[16:]*(expanded//2)
        else:assert r['op']==b[0] and payload==b[16:] and expanded==r['expanded']
        s,=[x for x in spi if abs(x['clock']-push)<=1]
        load,ack=(one([x for x in cpu[954] if x['index']==idx],k)['clock'] for k in ('load','ack'))
        assert prepare<=r['clock']<=w['clock']<=s['start']<=push+1 and push<=load<=ack
        assert b[0]!=3 or end<last<=s['start']
        rows.append(dict(op=b[0],section=b[1],offset=at,payload_B=n,expanded_B=expanded,
            payload_ready_ms=rel(r['clock']),header_ready_ms=rel(w['clock']),SPI_start_ms=rel(s['start']),
            published_ms=rel(push),SNES_accept_ms=rel(load),SNES_ack_ms=rel(ack),
            depth_at_push=bisect_right(pushes,push)-bisect_right(retired,push),
            before_END=push<end,before_last_tile_ack=push<last))
    return dict(rows=rows,source_last_write_ms={k:rel(v) for k,v in frozen['last_writes'].items()},
        validated_source_ms=rel(prepare),end_call_ms=rel(one(events,'end_enter')['clock']),
        end_accept_ms=rel(end),last_tile_ACK_ms=rel(last),SEAL_load_ms=rel(head['clock']),SEAL_line=head['line'],
        first_wait_line=waits[0]['line'] if waits else None,display_ms=rel(reveal['clock']),display_line=reveal['line'],
        before_head=head['frame']-prev['frame'],display_VB=reveal['frame']-prev['frame'],
        DMA_before_final_B=commands,frame_PPU_DMA_B=sum(r['value'] for r in cpu[954] if r['event']=='ppu_dma'),
        final_gate=beam,
        final_ROM_windows=grants,last_ROM_response_ms=rel(final_reads[-1][3]),
        early_counts={k:sum(r[k] for r in rows) for k in ('before_END','before_last_tile_ack')})


def analyze(a):
    cal=Calendar(a.traces/'nes-service509-rom03')
    earlier=read(ROOT/'analysis/map553-verification.json')
    client=read(ROOT/'analysis/upload550-verification.json')['client']
    rows=[]
    for i in (1,2):
        old=earlier['phases'][i-1]['variants']['map']['cost']
        base=a.traces/f'nes-prelude554-base{i}'
        assert all(sha(base/n)==old['pins'][n] for n in ('window.csv','packets.jsonl','seal528.csv'))
        both={}
        for mode,arm in [('base',a.base),('early',a.arm),('cut',a.cut)]:
            f=a.traces/f'nes-prelude554-{mode}{i}'
            m=inspect_run(f,a.plans,cal,base,sha(arm/'obj-nes-100/firmware.stm'),client,first_bg_limit=3)
            audit=read(a.traces/f'nes-prelude554-{mode}-audit{i}'/'audit.json')
            assert audit['frames']==53 and audit['trace']==m['pins']['window.csv']
            both[mode]=dict(cost=m,schedule=packet_schedule(f,cal),maps957=map_times(f),
                            beam957=last_frame(f)['beam'],replay=audit)
        ref=both['base']
        assert not ref['schedule']['early_counts']['before_last_tile_ack']
        for mode in ('early','cut'):
            new=both[mode]
            d=compare(new['cost'],ref['cost'])
            later=[g for g,b in new['cost']['BG'].items() if b['relative_window']>ref['cost']['BG'][g]['relative_window']]
            safe=(new['cost']['dense_frames'][952]['before_head']<=5 and not any(new['cost']['waits'].values()) and
                  not new['beam957']['waits'] and sum(r['push_minus_last_tile_ACK_ms']<0 for r in new['maps957']['maps'])>=2)
            intervals=lambda r:sum(r['cost']['dense_frames'][953][k] for k in ('before_head','after_head'))
            new.update(delta=d,later_first_BG=later,gate=safe and not later and all(v<0 for v in d.values())
                       and new['schedule']['before_head']<ref['schedule']['before_head']
                       and new['schedule']['display_VB']<ref['schedule']['display_VB'] and intervals(new)<=intervals(ref))
        rows.append(dict(phase=i,variants=both))
    guards={}
    for name,arm,prefix in [('early',a.arm,''),('cut',a.cut,'cut-')]:
        image=arm/'obj-nes-100/firmware.stm'
        bundle={k:read(a.checks/(prefix+k+'.json')) for k in ('guards','map','credit','menu','window','reports')}
        assert sha(image)==bundle['guards']['sha']==bundle['map']['sha']==bundle['credit']['sha']==bundle['menu']['firmware']==bundle['window']['firmware_SHA256']==bundle['reports']['after']['firmware']
        guards[name]=bundle
    stopped=read(a.traces/'nes-prelude554-stop02'/'result.json')
    assert len(stopped)==3 and all(r['commits']==49 and r['status']==228 for r in stopped)
    return dict(phases=rows,gate={m:all(p['variants'][m]['gate'] for p in rows) for m in ('early','cut')},
                guards=guards,staged_STOP=stopped,
                scope='Two matched 53-capture simulations, fixed CPI/ROM grant calendar. Physical FPS unmeasured.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','arm','cut','traces','plans','checks','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
