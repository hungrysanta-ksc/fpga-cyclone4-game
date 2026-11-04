"""Reconcile E8 snapshots, ROM response and frame-957 idle/SEAL DMA on both phases."""
import argparse
from bisect import bisect_right
import csv
from itertools import groupby
import json
from pathlib import Path

from analyze_nes_phase537 import ROOT, csv_groups, ms, one, read, sha
from budget_nes_planner607 import phase
from check_nes_game478 import crc
from test_nes_banks557 import host_after
from test_nes_raw506_joint import MASTER


def trace(folder,plans):
    events=read(folder/'events.json')
    obj=read(folder/'obj-phases.json')
    cpu=csv_groups(folder/'window.csv')
    pushes=[json.loads(l)[1] for l in (folder/'packets.jsonl').read_text().splitlines()]
    acks=sorted(r['clock'] for rows in cpu.values() for r in rows if r['event']=='ack')
    by_frame={}
    for g in (952,954,957):
        group=[e for e in events if e['generation']==g]
        prior=one([e for e in cpu[g-1] if e['op']==3],'reveal')['clock']
        rel=lambda clock:round(ms(clock-prior),6)
        last_ordinary=max(e['clock'] for e in group if e.get('opcode')=='0xe1' and e['packet_opcode'] not in (3,7))
        rom=obj[str(g)]['last_obj_rom_response']
        snapshots=[];previous=None;credit=[]
        for e in group:
            if e.get('opcode')=='0xe0':
                b=bytes.fromhex(e['reply'])
                sent=int.from_bytes(b[3:5],'big');retired=int.from_bytes(b[5:7],'big')
                assert b[1]==0xf7 and crc(b[1:19],8,7,0)==b[19]
                assert (sent,retired)==(bisect_right(pushes,e['start']),bisect_right(acks,e['start']))
                assert 0<=sent-retired<=4
                credit.append(sent-retired)
            if e.get('opcode')!='0xe8':
                continue
            b=bytes.fromhex(e['reply'])
            assert len(b)==20 and b[1:3]==bytes([0xd7,4]) and crc(b[1:19],8,7,0)==b[19]
            snap=host_after(e['start']+7.5*MASTER/2625000,3)
            assert snap<e['clock']
            snapshots.append(dict(ms=rel(snap),flags=b[3],count=int.from_bytes(b[4:6],'big'),
                token=int.from_bytes(b[14:18],'little') if b[6] else None,
                unchanged=b==previous,after_ordinary=snap>=last_ordinary,tail_empty=last_ordinary<=snap<rom and not b[6]))
            previous=b
        bulk=[s for s in snapshots if s['token'] is not None and s['flags']==2]
        assert bulk
        bursts=[]
        for (flags,count,token),samples in groupby(snapshots,lambda s:(s['flags'],s['count'],s['token'])):
            samples=list(samples)
            bursts.append(dict(flags=flags,count=count,token=token,samples=len(samples),
                               first_ms=samples[0]['ms'],last_ms=samples[-1]['ms']))
        final_bulk=next(s for s in bulk if s['token']==bulk[-1]['token'])
        by_frame[g]=dict(bursts=bursts,E8=len(snapshots),E0_checked=len(credit),max_unretired=max(credit),
            repeat=sum(s['unchanged'] for s in snapshots),
            after_last_ordinary_empty_before_ROM=sum(s['tail_empty'] for s in snapshots),
            last_ordinary_ms=rel(last_ordinary),last_ROM_ms=rel(rom),
            last_bulk_first_sample_after_ROM_ms=round(final_bulk['ms']-rel(rom),6))
        if g in (952,954):
            sealed=next(e['clock'] for e in group if e.get('opcode')=='0xe1' and e['packet_opcode']==3)
            cutoff=sealed-0.010*MASTER
            service=[r for r in obj[str(g)]['rom_service'] if r[0]==1]
            records=[bytes.fromhex(h) for _,h in read(plans/f'frame{g}/plans.json')]
            slots={int.from_bytes(q[2:4],'little'):q for q in records if q[6]==1}
            at=0;late=[]
            before_cutoff=set();after_cutoff=[]
            for issued in obj[str(g)]['obj_plans']:
                slot=issued['slot'];q=slots[slot];n=2*q[7].bit_count()
                batch=service[at:at+n];at+=n
                assert len(batch)==n and issued['accepted_clock']<=batch[0][1]
                tag=int.from_bytes(q[4:6],'little')
                lanes=[j for j in range(16) if q[7]>>(j//2)&1]
                for j,event in zip(lanes,batch):
                    alt=int.from_bytes(q[24+j//2*2:26+j//2*2],'little')
                    plane_tag=alt if j%2==0 and alt!=65535 else tag
                    assert q[8+j]<8 and plane_tag<8192
                    address=16*plane_tag+8*(j%2)+q[8+j]
                    if event[3]<=cutoff:
                        before_cutoff.add(address)
                    else:
                        after_cutoff.append(address)
                count=sum(r[3]>cutoff for r in batch)
                if count:
                    late.append(dict(slot=slot,tag=int.from_bytes(q[4:6],'little'),late_B=count,
                        accepted_ms=rel(issued['accepted_clock']),request_ms=rel(batch[0][1]),grant_ms=rel(batch[0][2])))
            assert at==len(service) and service[-1][3]==rom
            by_frame[g]['deadline']=dict(SEAL_ms=rel(sealed),ten_ms_earlier_ms=rel(cutoff),
                tail_after_final_ROM_ms=round(ms(sealed-rom),6),late_slots=late,
                late_unique_OBJ_B=len(set(after_cutoff)),late_OBJ_reads_seen_before=sum(
                    addr in before_cutoff for addr in after_cutoff))
    rows=cpu[957];sealed=[r for r in rows if r['op']==3]
    head=one(sealed,'load')['clock'];entry=one(sealed,'final212')['clock']
    idle=[r for r in rows if r['event']=='ppu_dma' and r['clock']<head]
    pre=[r for r in rows if r['event']=='idle524']
    assert len(idle)==len(pre)
    early=[dict(line=r['line'],clock=r['clock'],B=r['value'],
                map_offset=s['value']-65536 if s['value']>=65536 else None) for r,s in zip(idle,pre)]
    seal=csv_groups(folder/'seal528.csv')[957]
    dma=[dict(src=r['src'],dst=r['dst'],B=r['bytes']) for r in seal if r['event']=='dma' and r['clock']<entry]
    final=one(seal,'final_credit');latch=[r for r in seal if r['event']=='latch' and r['clock']>=entry]
    assert len(latch)<=1 and (latch or final['bytes']>=1568)
    palette=[]
    for start in [r for r in rows if r['op']==4 and r['section']==3 and r['event']=='load']:
        ack=one([r for r in rows if r['index']==start['index']],'ack')
        chunks=[r['value'] for r in rows if r['index']==start['index'] and r['event']=='zero_dma']
        palette.append(dict(index=start['index'],load_to_ack_ms=round(ms(ack['clock']-start['clock']),6),chunks=chunks))
    return dict(frames=by_frame,tail957=dict(early=early,SEAL_DMA=dma,remaining_credit=final['bytes'],
        final_credit_line=final['line'],sample_line=latch[0]['line'] if latch else None,
        sample_h=latch[0]['h'] if latch else None,waits=sum(r['event']=='wait169' and r['clock']>=entry for r in sealed),
        palette=palette))


def selector(folder, reference):
    audit=read(folder/'audit.json')
    assert audit['trace']==sha(reference/'window.csv') and audit['frames']==53
    with (folder/'selector536.csv').open() as f:
        probes=list(csv.DictReader(f))
    pushes=[json.loads(l)[1] for l in (reference/'packets.jsonl').read_text().splitlines()]
    result=[]
    for r,z in zip(probes,probes[1:]):
        if r['event']=='priority524' and z['event']=='skip8_523':
            # On STOP-free 957 the guard defers iff the next head is available.
            idx=int(r['index']);push=pushes[idx-1];clk=int(r['clock'])
            assert push<=int(z['clock'])
            result.append(dict(index=idx,priority_clk=clk,push_clk=push,line=int(r['line']),
                               selected_B=int(r['n']),tail_B=int(r['tail_B']),tail_src=int(r['tail_src'])))
    return dict(audit=audit,selector_hash=sha(folder/'selector536.csv'),preemptions=result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','plans','calendar','client','firmware','report'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--run-prefix',required=True)
    a=p.parse_args()
    fixed=read(ROOT/'analysis/planner607-recent-verification.json')['phases']
    result=[]
    for i in (1,2):
        recent=a.traces/f'nes-planner607-recent{i}'
        assert all(sha(recent/n)==h for n,h in fixed[i-1]['candidate']['pins'].items())
        entry=phase(a,i,a.run_prefix)
        entry['recent607']=fixed[i-1]['candidate']
        entry['traces']={k:trace(a.traces/f'{v}{i}',a.plans) for k,v in [('MMC577','nes-close561-run'),('recent607','nes-planner607-recent'),('candidate',a.run_prefix)]}
        entry['selector607']=selector(a.traces/f'nes-quiet608-selectorC{i}',recent)
        result.append(entry)
    a.report.write_text(json.dumps(dict(phases=result,ARM=sha(a.firmware),client=sha(a.client/'sink165.sfc'),
        firmware_B=a.firmware.stat().st_size),indent=2)+'\n',encoding='utf8')
