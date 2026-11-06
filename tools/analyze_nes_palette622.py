# SPDX-License-Identifier: MIT
"""Match actual ARM pushes, SNES head/ACKs and idle vs sealed PPU writes on 957."""
import argparse
import json
from pathlib import Path

from analyze_nes_bank621 import Calendar, csv_groups, lanes, ms, one, read, schedule, sha, work
from analyze_nes_bg620 import read_lines


def detail(folder):
    rows=csv_groups(folder/'window.csv')[957]
    packets=read_lines(folder/'packets.jsonl')
    pushes={round(e['clock']):e for e in read(folder/'events.json') if e['generation']==957 and e.get('opcode')=='0xe1'}
    lookup={(r['index'],r['event']):r for r in rows if r['event'] in ('load','ack')}
    commands=[]
    map_ready={}
    bg_ready={}
    for r in rows:
        if r['event']!='load' or (r['op'],r['section']) not in ((7,0),(2,3),(4,3),(2,2),(4,2)):
            continue
        idx=r['index']
        _,push,h,_=packets[idx-1]
        b=bytes.fromhex(h)
        off=int.from_bytes(b[10:12],'little')
        size=int.from_bytes(b[12:14] if b[0]==2 else b[14:16],'little')
        e,=[pushes[t] for t in range(push-1,push+2) if t in pushes]
        ack=lookup[idx,'ack']
        assert e['start']<push<=r['clock']<ack['clock'] and (b[0],b[1])==(r['op'],r['section'])
        if r['section']==2:
            for pos in range(off,off+size,64):
                assert pos not in map_ready
                map_ready[pos]=ack['clock']
        else:
            commands.append(dict(section=b[1],offset=off,B=size,issue=e['start'],push=push,
                                 load=r['clock'],line=r['line'],accepted=ack['clock'],ack_line=ack['line']))
            if b[1]==0:
                bg_ready[off,size]=ack['clock']
    assert set(bg_ready)=={(0,16),(2112,48)}
    tiles={x['clock']:x for x in csv_groups(folder/'tile532.csv').get(957,[]) if x['event']=='tile'}
    grants=[]
    for i,r in enumerate(rows):
        if r['event']!='idle524':
            continue
        start,end=rows[i+1:i+3]
        n=start['value']
        assert start['event']=='ppu_dma' and end['event']=='ppu_last'
        assert start['frame']==end['frame'] and 225<=start['line']<=end['line']<=261
        if r['value']>=65536:
            off=r['value']-65536
            assert all(map_ready[p]<start['clock'] for p in range(off,off+n,64))
            kind='map'
        else:
            t=tiles[r['clock']]
            off=t['dst']
            assert t['n']==n
            kind='tile'
            if (off,n) in bg_ready:
                assert bg_ready[off,n]<start['clock']
        grants.append(dict(kind=kind,offset=off,B=n,frame=start['frame'],line=start['line'],end_line=end['line'],
                           first=start['clock'],last=end['clock']))
    map_frames={g['frame'] for g in grants if (g['kind'],g['offset'],g['B'])==('map',2048,1152)}
    target={(0,16),(2112,48)}
    early={(g['offset'],g['B']) for g in grants if g['kind']=='tile'} & target
    together=any(all(any(g['kind']=='tile' and (g['offset'],g['B'])==b and g['frame']==f for g in grants)
                     for b in target) for f in map_frames)
    sealed=[(r['dst'],r['bytes']) for r in csv_groups(folder/'seal528.csv')[957] if r['event']=='dma' and r['port']==24]
    for b in target:
        assert int(b in early)+sealed.count(b)==1
    return dict(commands=commands,grants=grants,early_tile_B=sum(n for _,n in early),
                early_map1152=bool(map_frames),same_VBlank=together)


def compare(a):
    archived=read(a.reference)
    calendar=Calendar(a.calendar)
    addresses=[addr for _,h in read(a.plans/'frame954/plans.json') for q in [bytes.fromhex(h)] if q[6]==0 for _,addr in lanes(q)]
    guards={**read(a.build/'guards.json'),**read(a.build/'split-guards.json'),**read(a.build/'credit-guards.json')}
    phases=[]
    for i in (1,2):
        base=a.traces/f'nes-bank621-arm01-{i}'
        pinned=archived['phases'][i-1]
        baseline=read(base/'joint.json')
        costs={}
        payload=work(base)
        for name in ['621',*guards]:
            d=base if name=='621' else a.traces/f'nes-palette622-{name}-{i}'
            j=read(d/'joint.json')
            r=schedule(d,calendar,addresses)
            if name=='621':
                assert r['pins']==pinned['trial']['pins']
            else:
                assert j['firmware_SHA256']==guards[name]['arm']==sha(a.build/name/'src/obj-nes-100/firmware.stm')
                assert all(j[k]==baseline[k] for k in ('client_SHA256','parameters','vram_DMA_B','ROM_read_allocations'))
                assert work(d)==payload
                assert all(sha(d/f)==sha(base/f) for g in range(905,958) for f in (f'frame-{g}.rgb',f'map-{g}.bin'))
            local=detail(d)
            costs[name]=dict(detail=local, dense_VB=r['dense_VB'],dense_ms=r['dense_mean_ms'],last_ACK=r['last_ACK'],
                             delta619_ms=ms(r['last_ACK']-pinned['reference']['last_ACK']),
                             delta621_ms=ms(r['last_ACK']-pinned['trial']['last_ACK']),intervals=r['intervals'],
                             from_display956_to_ACK_ms=ms(r['last_ACK']-r['g957']['clocks']['previous_display']),
                             previous_display_clock=r['g957']['clocks']['previous_display'],
                             display906=r['g906']['display_VB'],map955=[r['first_map_955_B'],r['last_map_955_B']],
                             final_wait_957=r['final_wait_957'],ROM96=r['ROM96_in_first_window'],
                             terminal=r['terminal_957'],max_slots=r['max_bulk_banks'],VRAM_B=r['VRAM_DMA_B'],
                             pins=r['pins'],wire_B=r['wire_B'])
            c=costs[name]
            c['guards_ok']=bool(c['display906']==9 and c['intervals'][952]==c['intervals'][954]==4 and c['ROM96']==96
                                and c['map955'][0]>=192 and c['map955'][1]==384 and not c['final_wait_957'])
            c['pass_vs_619']=c['guards_ok'] and local['same_VBlank'] and c['delta619_ms']<0
            c['pass']=c['pass_vs_619'] and c['delta621_ms']<0
        phases.append(costs)
    edges=a.traces/'nes-palette622-after-pack-edges/edges.json'
    stop=a.traces/'nes-palette622-after-pack-stop/result.json'
    checks=read(edges);stops=read(stop)
    assert {r['case'] for r in checks if r['grant']==0}>={'head','stop','both'}
    assert {(r['generation'],r['fault']) for r in checks if 'fault' in r}=={(g,f) for g in (906,907) for f in ('missing','duplicate')}
    assert {(r['generation'],r['boundary'],r['status']) for r in stops}=={(g,k,0xe4) for g in (906,907) for k in ('budget538','final212')}
    replays=[read(a.traces/f'nes-palette622-replay-{i}/audit.json') for i in (1,2)]
    assert all(r['baseline']['ACK']==p['621']['last_ACK'] for r,p in zip(replays,phases))
    pack_replays=[read(a.traces/f'nes-palette622-pack-replay-{i}/audit.json') for i in (1,2)]
    assert all(r['baseline']['ACK']==p['after-pack']['last_ACK'] for r,p in zip(pack_replays,phases))
    result=dict(phases=phases,replays=replays,after_pack_replays=pack_replays,passes={m:all(p[m]['pass'] for p in phases) for m in guards},
                passes_vs_619={m:all(p[m]['pass_vs_619'] for p in phases) for m in guards},
                guards=guards,shared_client_guards=dict(priority=checks,STOP=stops),
                Flash_B={m:(a.build/m/'src/obj-nes-100/firmware.stm').stat().st_size for m in guards})
    result['over_Flash_B']={}
    for m in ('small-bg','shared-order','small-shared-cost'):
        image=a.build/m/'src/obj-nes-100/firmware.stm'
        assert image.stat().st_size>212992
        result['over_Flash_B'][m]=dict(size=image.stat().st_size,excess=image.stat().st_size-212992,sha=sha(image))
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('build','traces','plans','reference','calendar','out'):
        p.add_argument('--'+k,type=Path,required=True)
    compare(p.parse_args())
