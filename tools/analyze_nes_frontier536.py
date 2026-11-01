# SPDX-License-Identifier: MIT
"""Join real E0 snapshots, packet publication, CPU ACKs and the empty-head VBlank selector."""
import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path

from analyze_nes_map526 import ROOT,Calendar,ms,read,run_cost,sha,tiles
from analyze_nes_output531 import csv_groups,one,prior_blank_windows
from analyze_nes_quiet528 import packet_content


def contents(folder):
    ordinary=Counter()
    image={}
    for line in (folder/'packets.jsonl').read_text().splitlines():
        _,_,header,payload=json.loads(line)
        b=bytes.fromhex(header)
        if b[1]!=5 or b[0] not in (2,4,5):
            ordinary[(b[:2]+b[4:],payload)]+=1
            continue
        g=int.from_bytes(b[8:10],'little');at=int.from_bytes(b[10:12],'little')
        n=int.from_bytes(b[12:14],'little');data=b[16:]
        assert len(data)==n
        if b[0]!=2:
            length=int.from_bytes(b[14:16],'little')
            assert n==2 and length%2==0
            data*=length//2
        for i,v in enumerate(data):
            key=(g,at+i);assert key not in image
            image[key]=v
    return ordinary,image


def ledger(folder,audit):
    cpu=csv_groups(folder/'window.csv');beam=csv_groups(folder/'seal528.csv')
    probes=csv_groups(audit/'selector536.csv')
    records=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    pushes=[r[1] for r in records];packets=[bytes.fromhex(r[2]) for r in records]
    events=read(folder/'events.json')
    writes=[r for r in events if r['event']=='SPI' and r['opcode']=='0xe1']
    assert len(writes)==len(pushes) and all(abs(r['clock']-t)<=1 for r,t in zip(writes,pushes))
    loads={r['index']:r for rows in cpu.values() for r in rows if r['event']=='load'}
    acks=sorted((r for rows in cpu.values() for r in rows if r['event']=='ack'),key=lambda r:r['index'])
    assert [r['index'] for r in acks]==list(range(1,len(pushes)+1))
    retired=[r['clock'] for r in acks]
    status=[]
    for r in events:
        if r['event']!='SPI' or r['opcode']!='0xe0':continue
        b=bytes.fromhex(r['reply']);assert len(b)==20 and b[1]==0xf7
        sent=int.from_bytes(b[3:5],'big');done=int.from_bytes(b[5:7],'big')
        assert sent==bisect_right(pushes,r['start']) and done==bisect_right(retired,r['start'])
        status.append((r['start'],r['clock'],sent,done))
    result={}
    for g,offset in ((910,1216),(951,2560)):
        group=[r for r in events if r['generation']==g];start=one(group,'source_begin')['clock']
        def rel(t):return ms(t-start)
        c=cpu[g];seal=one([r for r in c if r['op']==3],'load')
        opened=one([r for r in c if r['op']==1],'ack')['clock']
        stop=pushes[seal['index']-1]
        anchor=next(r for r in beam[g] if r['event']=='dma')
        f=next(r['frame'] for r in c if r['clock']==anchor['clock'] and r['event']=='ppu_dma')
        windows=[]
        for lo,hi in prior_blank_windows(anchor,f,opened,stop,254):
            gaps=[]
            busy=[]
            for r in c:
                if r['event']!='ack':continue
                idx=r['index'];left=max(lo,loads[idx]['clock']);right=min(hi,r['clock'])
                if left<right:
                    b=packets[idx-1];busy.append(dict(index=idx,op=b[0],section=b[1],offset=int.from_bytes(b[10:12],'little'),ms=ms(right-left)))
                if idx<len(pushes):
                    left=max(lo,r['clock']);right=min(hi,pushes[idx])
                    if right>left:gaps.append([rel(left),rel(right)])
            seen=[r for r in probes[g] if lo<=r['clock']<hi]
            # At priority524 the CPU reads STOP, then the queue head. In these
            # successful commits STOP is clear. A direct skip is a new head.
            preempted=[rel(r['clock']) for r,z in zip(probes[g],probes[g][1:])
                       if lo<=r['clock']<hi and r['event']=='priority524' and z['event']=='skip8_523']
            grants=[dict(offset=r['value']-65536 if r['value']>=65536 else None,B=c[i+1]['value'],at_ms=rel(r['clock']))
                    for i,r in enumerate(c) if r['event']=='idle524' and lo<=r['clock']<hi]
            windows.append(dict(open_ms=rel(lo),close_ms=rel(hi),queue_at_open=bisect_right(pushes,lo)-bisect_right(retired,lo),
                                empty=gaps,head_service=busy,probes=dict(Counter(r['event'] for r in seen)),
                                new_head_preempted_ms=preempted,grants=grants))
        maps=[]
        for i,b in enumerate(packets):
            if int.from_bytes(b[8:10],'little')!=g or b[1]!=2 or b[0] not in (2,4):continue
            at=int.from_bytes(b[10:12],'little')
            length=int.from_bytes(b[12:14] if b[0]==2 else b[14:16],'little')
            enter,=[r for r in group if r['event']=='map_packet_enter' and r['offset']==at]
            enqueue,=[r['clock'] for r in group if r['event']=='map_enqueue' and r['offset']==at]
            spi=writes[i];cached=next(s for s in reversed(status) if s[1]<=enqueue)
            observed=next(s for s in status if s[3]>=i+1)
            refresh=[dict(start_ms=rel(s[0]),seen_ms=rel(s[1]),sent=s[2],retired=s[3])
                     for s in status if enqueue<=s[0]<spi['start']]
            assert enter['clock']<=enqueue<=spi['start']<=pushes[i]<=loads[i+1]['clock']<=retired[i]<=observed[0]
            maps.append(dict(index=i+1,offset=at,B=length,early=enter['early'],enter_ms=rel(enter['clock']),enqueue_ms=rel(enqueue),
                             pre_enqueue_ops=[dict(op=z['opcode'],packet_op=z['packet_opcode'],at_ms=rel(z['start']))
                                              for z in group if z['event']=='SPI' and enter['clock']<=z['start']<enqueue],
                             actual_pending=i-bisect_right(retired,enqueue),cached_pending=i-cached[3],E1_start_ms=rel(spi['start']),
                             PUSH_ms=rel(pushes[i]),load_ms=rel(loads[i+1]['clock']),accept_credit_ms=rel(retired[i]),
                             ARM_E0_seen_ms=rel(observed[1]),enqueue_refresh=refresh,
                             credit_needed_return_ms=rel(retired[i-4]) if i-cached[3]>=4 else None))
        target,=[r for r in maps if r['offset']<=offset<r['offset']+r['B']]
        result[g]=dict(windows=windows,maps=maps,row_offset=offset,target=target,SEAL_load_ms=rel(seal['clock']))
    return result


def analyze(a):
    prior=read(ROOT/'analysis/tile532-verification.json')
    released=read(ROOT/'analysis/trial533-verification.json')
    assert sha(a.arms[0]/'obj-nes-100/firmware.stm')==released['firmware_SHA256']
    plans={r['generation']:r for r in read(ROOT/'analysis/obj518-verification.json')['plans']['frames']}
    oracle=tiles(a.fixture,957);calendar=Calendar(a.calendar)
    refs=read(ROOT/'analysis/prefix523-verification.json')['phases'];phases=[]
    for i in range(2):
        variants={};base=a.base[i]
        for name,folder,arm,audit in [('base',base,a.arms[0],a.audit_base[i]),('front',a.front[i],a.arms[1],a.audit_front[i]),('raw',a.raw[i],a.arms[2],a.audit_raw[i])]:
            fw=arm/'obj-nes-100/firmware.stm'
            cost,_=run_cost(folder,'row254',dict(refs[i]['candidate'],firmware=sha(fw)),plans,calendar,oracle,map_chunk=128)
            published=prior['phases'][i]['variants']['pair']
            assert cost['client']==published['client'] and cost['dma_B']==published['dma_B'] and cost['ROM_reads']==published['ROM_reads']
            if name=='base':
                assert cost['final_ack']==published['final_ack'] and cost['pins']['window.csv']==published['pins']['window.csv']
                canonical=contents(base);canonical_packets=packet_content(base)
            else:
                assert contents(folder)==canonical
                if name=='front':assert packet_content(folder)==canonical_packets
                assert all(sha(folder/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,958))
            audit_result=read(audit/'audit.json')
            assert audit_result['frames']==53 and audit_result['trace']==cost['pins']['window.csv']
            assert sha(audit/'tile532.csv')==sha(folder/'tile532.csv')
            assert not any((folder/n).exists() for n in ('map-error.txt','callback-error.txt'))
            rows=cost.pop('frames');cost['dense_VBlanks']=sum(r['display_VBlanks'] for r in rows if 951<=r['g']<=955)
            cost['targets']={r['g']:r for r in rows if r['g'] in (910,951,952,954)}
            cpu=csv_groups(folder/'window.csv')
            dense=[]
            for g in range(951,956):
                previous=one([r for r in cpu[g-1] if r['op']==3],'reveal')
                seal=[r for r in cpu[g] if r['op']==3]
                load,reveal=one(seal,'load'),one(seal,'reveal')
                dense.append(dict(g=g,prior_display_to_SEAL_frames=load['frame']-previous['frame'],
                                  SEAL_to_display_frames=reveal['frame']-load['frame'],
                                  prior_display_to_SEAL_ms=ms(load['clock']-previous['clock']),
                                  SEAL_to_display_ms=ms(reveal['clock']-load['clock'])))
            assert sum(r['prior_display_to_SEAL_frames']+r['SEAL_to_display_frames'] for r in dense)==cost['dense_VBlanks']
            cost['dense_display']=dense
            cost['queue']=ledger(folder,audit);cost['audit']=audit_result
            cost['last_ACK_change_ms']=ms(cost['final_ack']-published['final_ack'])
            cost['firmware']=sha(fw);cost['Flash_B']=fw.stat().st_size
            cost['BSS_B']=int((arm.parent/'size.log').read_text().splitlines()[-1].split()[2])
            variants[name]=cost
        phases.append(variants)
    gates={k:all(p[k]['dense_VBlanks']<p['base']['dense_VBlanks'] and p[k]['dense_ms']<p['base']['dense_ms'] and p[k]['last_ACK_change_ms']<0
                 and all(p[k]['targets'][g]['final_waits']==0 for g in (952,954)) for p in phases) for k in ('front','raw')}
    guards={}
    for name,arm_file,snes_dir in zip(('front','raw'),a.arm_guards,a.snes_guards):
        arm=read(arm_file);snes=read(snes_dir/'result.json')
        assert arm['firmware']==phases[0][name]['firmware'] and len(arm['second'])==11 and len(arm['first'])==9 and len(arm['end'])==6
        assert len(snes)==22
        guards[name]=dict(ARM=arm,SNES=snes)
    return dict(phases=phases,gates=gates,guards=guards)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','front','raw','audit-base','audit-front','audit-raw','arm-guards','snes-guards'):p.add_argument('--'+n,nargs=2,required=True,type=Path)
    p.add_argument('--arms',nargs=3,required=True,type=Path)
    for n in ('fixture','calendar','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
