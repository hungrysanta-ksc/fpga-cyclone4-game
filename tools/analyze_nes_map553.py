# SPDX-License-Identifier: MIT
"""Join immutable map content, ordered E1 arrivals, 65816 loads/ACKs and E0 credits."""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
from analyze_nes_hardware552 import tail
from analyze_nes_phase537 import ROOT, Calendar, csv_groups, ms, one, read, sha
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare
from analyze_nes_upload550 import last_frame


def map_times(folder):
    cpu=csv_groups(folder/'window.csv')
    events=[r for r in read(folder/'events.json') if r['generation']==957]
    origin=one(events,'output_enter531')['clock']
    rel=lambda t:round(ms(t-origin),6)
    frozen=one(events,'bg_map_frozen')
    image=(folder/'map-957.bin').read_bytes()
    assert len(image)==4096 and hashlib.sha256(image).hexdigest()==frozen['sha256']
    packets=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    pushes=[r[1] for r in packets]
    retired=sorted(r['clock'] for group in cpu.values() for r in group if r['event']=='ack')
    status=[]
    for r in events:
        if r.get('opcode')=='0xe0':
            b=bytes.fromhex(r['reply'])
            sent=int.from_bytes(b[3:5],'big');done=int.from_bytes(b[5:7],'big')
            assert b[1]==0xf7 and (sent,done)==(bisect_right(pushes,r['start']),bisect_right(retired,r['start']))
            status.append((r['clock'],done))
    def event(idx,k):
        return one([r for r in cpu[957] if r['index']==idx],k)['clock']
    tiles=[(r['index'],r['clock']) for r in cpu[957] if r['op']==7 and r['event']=='ack']
    result=[]
    for idx,(_,t,h,_) in enumerate(packets,1):
        b=bytes.fromhex(h)
        at=int.from_bytes(b[10:12],'little')
        if int.from_bytes(b[8:10],'little')!=957 or b[:2]!=b'\x02\x02' or at not in (3008,3200,3392):continue
        assert len(b)==208 and b[16:]==image[at:at+192]
        entry,enqueue=(one([r for r in events if r.get('offset')==at],k)['clock'] for k in ('map_packet_enter','map_enqueue'))
        load,ack=(event(idx,k) for k in ('load','ack'))
        observed=next(time for time,done in status if done>=idx)
        assert frozen['clock']<entry<=enqueue<=t<=load<=ack<=observed
        pending=[j for j,end in tiles if j<idx and end>t]
        result.append(dict(offset=at,entry_ms=rel(entry),enqueue_ms=rel(enqueue),push_ms=rel(t),
            load_ms=rel(load),ack_ms=rel(ack),ARM_credit_ms=rel(observed),
            queue_depth_after_push=idx-bisect_right(retired,t),pending_earlier_tiles=pending,
            push_minus_last_tile_ACK_ms=ms(t-tiles[-1][1])))
    assert [r['offset'] for r in result]==[3008,3200,3392]
    return dict(frozen_ms=rel(frozen['clock']),prepare_ms=rel(one(events,'prepare_enter')['clock']),
                final_tile_push_ms=rel(pushes[tiles[-1][0]-1]),final_tile_ack_ms=rel(tiles[-1][1]),maps=result)


def analyze(a):
    cal=Calendar(a.traces/'nes-service509-rom03')
    prior=read(ROOT/'analysis/upload550-verification.json')
    phases=[]
    for i in (1,2):
        physical=a.traces/f'nes-upload550-joint{i}'
        reference=prior['phases'][i-1]['measured']
        assert all(sha(physical/n)==h for n,h in reference['pins'].items())
        by_kind={}
        for kind,src in [('base',a.base),('map',a.arm)]:
            folder=a.traces/f'nes-map553-{kind}{i}'
            audit=read(a.traces/f'nes-map553-{kind}-audit{i}'/'audit.json')
            m=inspect_run(folder,a.plans,cal,physical,sha(src/'obj-nes-100/firmware.stm'),prior['client'],first_bg_limit=3)
            assert audit['frames']==53 and audit['trace']==m['pins']['window.csv']
            if kind=='base':
                assert all(m['pins'][n]==reference['pins'][n] for n in ('events.json','packets.jsonl','window.csv'))
            by_kind[kind]=dict(cost=m,maps=map_times(folder),audit=audit,beam957=last_frame(folder)['beam'],
                tails={g:tail(folder,g) for g in (951,953,957)})
        row=by_kind['map'];m=row['cost']
        controls={'MMC551':reference,'report_only':by_kind['base']['cost']}
        delta={label:compare(m,v) for label,v in controls.items()}
        later={label:[g for g,b in m['BG'].items() if b['relative_window']>v['BG'][g if label=='report_only' else str(g)]['relative_window']]
               for label,v in controls.items()}
        gate=(m['dense_frames'][952]['before_head']<=5 and not any(m['waits'].values()) and row['beam957']['waits']==0
              and not any(later.values()) and all(v<0 for d in delta.values() for v in d.values()))
        phases.append(dict(phase=i,variants=by_kind,delta=delta,later_first_BG=later,gate=gate))
    guards={k:read(a.checks/(k+'.json')) for k in ('guards','credit','window','menu','reports')}
    image=a.arm/'obj-nes-100/firmware.stm'
    assert guards['guards']['sha']==guards['credit']['sha']==guards['menu']['firmware']==guards['window']['firmware_SHA256']==sha(image)
    return dict(phases=phases,gate=all(p['gate'] for p in phases),guards=guards,Flash_B=image.stat().st_size,
                free_Flash_B=212992-image.stat().st_size,BSS_B=guards['window']['BSS_B'],
                scope='Matched real ARM and 65816, periodic boot ROM grants, fixed CPI, SPI and IRQ; no new physical FPS.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','base','arm','plans','checks','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
