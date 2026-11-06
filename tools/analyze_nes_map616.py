# SPDX-License-Identifier: MIT
"""Audit large-map grants, publication times and continuous display ACKs."""
import argparse
import json
from bisect import bisect_right
from collections import Counter
from pathlib import Path

from analyze_nes_dense519 import consumed_tiles
from analyze_nes_dma542 import partition
from analyze_nes_output531 import prior_blank_windows
from analyze_nes_phase537 import ROOT, contents, csv_groups, ms, one, read, sha
from analyze_nes_prefix523 import packet_trace, verified_visible_dma


def costs(folder, g=952):
    all_cpu = csv_groups(folder / 'window.csv')
    cpu = all_cpu[g]
    trace = csv_groups(folder / 'seal528.csv')[g]
    seal = [r for r in cpu if r['op']==3]
    head = one(seal,'load')
    final = one(seal,'final212')['clock']
    stop = one(seal,'ack')['clock']
    push = [json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    times = [r[1] for r in push]
    ret = sorted(r['clock'] for rows in all_cpu.values() for r in rows if r['event']=='ack')
    assert len(ret)==len(push)
    anchor = next(r for r in trace if r['event']=='dma')
    frame = one([r for r in cpu if r['clock']==anchor['clock'] and r['event']=='ppu_dma'],'ppu_dma')['frame']
    opened = one([r for r in cpu if r['op']==1],'ack')['clock']
    windows = sorted(prior_blank_windows(anchor,frame,opened,times[head['index']-1],254))
    # Offsets relative to the inactive map at A000; the selected command is AB80..ADFF.
    start,end = 0xb80,0xe00
    ready={}
    rows=[]
    early=set()
    for i,r in enumerate(cpu):
        if r['event']=='ack' and r['section']==2:
            h=bytes.fromhex(push[r['index']-1][2])
            field = 12 if h[0]==2 else 14
            at=int.from_bytes(h[10:12],'little')
            n=int.from_bytes(h[field:field+2],'little')
            for pos in range(at,at+n,64):
                assert pos not in ready
                ready[pos]=r['clock']
        if r['event']!='idle524' or r['value']<65536:
            continue
        dma=one(cpu[i+1:i+2],'ppu_dma')
        at=r['value']-65536
        n=dma['value']
        assert n and n%64==0 and at%64==0
        units=set(range(at,at+n,64))
        assert all(ready[p]<=r['clock'] for p in units) and early.isdisjoint(units)
        # A new packet arriving after the priority read can wait for the in-flight DMA.
        early.update(units)
        rows.append(dict(offset=at,B=n,line=r['line'],start_clock=r['clock'],
                         queue_at_grant=bisect_right(times,r['clock'])-bisect_right(ret,r['clock'])))
    assert all(p in ready for p in range(start,end,64))
    remaining=[]
    base=0xa000
    for r in trace:
        if r['event']=='dma' and r['port']==24 and r['clock']<final:
            lo=max(base+start,r['dst'])
            hi=min(base+end,r['dst']+r['bytes'])
            if lo<hi: remaining.extend(range(lo-base,hi-base))
    moved={b for pos in early for b in range(pos,pos+64) if start<=b<end}
    assert len(set(remaining))==len(remaining) and moved.isdisjoint(remaining)
    assert len(moved)+len(remaining)==end-start
    return dict(map_640_early_B=len(moved),SEAL_map_640_B=len(remaining),early_map=rows,
                accepted_relative_BEGIN_ms={p:round(ms(ready[p]-opened),6) for p in range(start,end,64)},
                windows=[dict(open_ms=ms(lo-opened),end_ms=ms(hi-opened),
                              accepted_at_open_B=64*sum(ready[p]<=lo for p in range(start,end,64)),
                              accepted_by_end_B=64*sum(ready[p]<hi for p in range(start,end,64))) for lo,hi in windows],
                credit=one(trace,'final_credit')['bytes'],
                beam=[(r['line'],r['h']) for r in trace if r['event']=='latch' and final<=r['clock']<=stop])


def compare(base,new,pins,client):
    for name,digest in pins.items():
        assert sha(base/name)==digest, name
    b,j=[read(d/'joint.json') for d in (base,new)]
    assert b['parameters']==j['parameters'] and b['firmware_SHA256']==j['firmware_SHA256']
    assert sha(client/'sink165.sfc')==sha(new/'client.sfc')==j['client_SHA256']
    assert j['passed'] and j['last_status']==1 and j['commits']==j['map_WRAM_VRAM_verified']==53
    assert j['max_bulk_banks']<=2 and b['vram_DMA_B']==j['vram_DMA_B']
    assert not any((new/n).exists() for n in ('fault.json','map-error.txt','callback-error.txt'))
    ordinary,raw=contents(base)
    other,newraw=contents(new)
    assert raw==newraw and consumed_tiles(base)==consumed_tiles(new)
    assert {k:v for k,v in ordinary.items() if k[0][0]!=7}=={k:v for k,v in other.items() if k[0][0]!=7}
    assert b['ROM_read_allocations']==j['ROM_read_allocations']
    rows,_,_,_=packet_trace(new)
    checked=verified_visible_dma([r for r in rows if int(r['g'])>=905])
    def series(d, joint):
        obj=read(d/'obj-phases.json')
        hits=Counter(row[5] for frame in obj.values() for row in frame.get('cache611',[]))
        assert sum(hits.values())==5616 and hits['BG_hit']==48 and hits['OBJ_capture']==1200
        events=read(d/'events.json')
        capture_ready={r['generation']:r['capture_ready'] for r in events if r['event']=='source_begin'}
        reuse=[capture_ready[g+2]-240*341*4-obj[str(g)]['ea'] for g in range(905,956)]
        assert min(reuse)>=0
        phases=partition(d)
        cpu=csv_groups(d/'window.csv')
        frames={}
        for g in range(905,958):
            c=[r for r in cpu[g] if r['op']==3]
            display=one(c,'reveal');ack=one(c,'ack');fin=one(c,'final212')['clock']
            assert ack['value']==1 and display['line']>=225 and display['frame']==ack['frame']
            assert ack['clock']==joint['frames'][g-905]['ACK_masterclock']
            frames[g]=(display['frame'],display['clock'],ack['clock'],sum(r['event']=='wait169' and r['clock']>=fin for r in c))
        def interval(g):
            return dict(VBlank=frames[g][0]-frames[g-1][0],ms=ms(frames[g][1]-frames[g-1][1]),
                        final_waits=frames[g][3],ack=frames[g][2])
        return dict(cache=hits,min_capture_reuse_ms=ms(min(reuse)),post_SEAL={g:phases[g] for g in (952,954,955,957)},
                    watched={g:interval(g) for g in (951,952,953,954,955,957)},
                    dense_VBlank=frames[955][0]-frames[950][0],dense_ms=ms(frames[955][1]-frames[950][1])/5,
                    last_ACK=frames[957][2],warm_ms=ms(frames[957][1]-frames[906][1])/51,
                    frame952=costs(d))
    for g in range(905,958):
        assert sha(base/f'frame-{g}.rgb')==sha(new/f'frame-{g}.rgb')
    before=series(base,b);after=series(new,j)
    assert before['frame952']['SEAL_map_640_B']==640
    return dict(before=before,after=after,checked_DMA=checked,delta_last_ACK_ms=ms(after['last_ACK']-before['last_ACK']),
                gate=(after['watched'][952]['final_waits']==after['watched'][957]['final_waits']==0
                      and after['watched'][952]['VBlank'] < before['watched'][952]['VBlank']
                      and after['frame952']['map_640_early_B'] > 0
                      and after['dense_ms'] < before['dense_ms']
                      and after['dense_VBlank']<before['dense_VBlank'] and after['last_ACK']<before['last_ACK']),
                pins={n:sha(new/n) for n in pins})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('traces','client','guards','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--staged-stop',type=Path,help='954 palette/OAM/HDMA cancellation results')
    parser.add_argument('--prefix',default='nes-map616-run')
    parser.add_argument('--fixed-prefix',help='Two 952-only audit directories numbered 1 and 2')
    args=parser.parse_args()
    ref=read(ROOT/'analysis/board611-verification.json')
    phases=[compare(args.traces/f'nes-board611-run{i}',args.traces/f'{args.prefix}{i}',
                    ref['phases'][i-1]['candidate']['pins'],args.client) for i in (1,2)]
    build=read(args.client/'build.json')
    guards=read(args.guards/'edges.json')
    last=build['map_last_line']
    assert build['body_bytes']==4949 and build['program_bytes']==5120 and build['map_chunk_B']==1152
    assert any(r.get('line')==last and r['case']=='late_stop' and r['size']==1152 for r in guards)
    assert any(r.get('line')==last+1 and r['case']=='stop' and r['grant']==0 for r in guards)
    assert {(r['generation'],r['fault']) for r in guards if 'fault' in r}=={
        (g, f) for g in (906,907) for f in ('missing','duplicate')}
    report=dict(last_line=last,body_B=build['body_bytes'],program_B=build['program_bytes'],scope='Coupled linked ARM and 65816, CPI=2, measured SPI driver costs and periodic ROM calendar. Hardware FPS and board timing not measured.',phases=phases,guards=guards,client_SHA256=sha(args.client/'sink165.sfc'),
                gate=all(p['gate'] for p in phases))
    if args.staged_stop:
        staged=read(args.staged_stop/'result.json')
        assert {r['boundary'] for r in staged}=={'staged-3','staged-4','staged-5'}
        assert all(r['status']==228 and r['commits']==49 and r['generation']==954 for r in staged)
        report['staged_STOP']=staged
    if args.fixed_prefix:
        fixed=[]
        for i in (1,2):
            a=read(args.traces/f'{args.fixed_prefix}{i}'/'audit.json')
            assert a['trace']==sha(args.traces/f'{args.fixed_prefix}{i}'/'window.csv')
            assert a['frames']==48 and a['identical_prefix_events']>0
            fixed.append(dict(**a,delta_ACK_ms=ms(a['after']['ACK']-a['before']['ACK'])))
        report['fixed_arrivals_952_only']=fixed
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
