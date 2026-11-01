# SPDX-License-Identifier: MIT
"""Attribute the beam miss to actual SEAL DMA commands and compare two continuous ARM runs."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_nes_map526 import ROOT, Calendar, ms, read, run_cost, sha, tiles


def seal(folder,g):
    with (folder/'seal528.csv').open() as f:
        samples=[{k:v if k=='event' else int(v) for k,v in r.items()} for r in csv.DictReader(f) if int(r['g'])==g]
    latch,=[r for r in samples if r['event']=='latch']
    with (folder/'window.csv').open() as f:
        trace=[r for r in csv.DictReader(f) if int(r['g'])==g and r['op']=='3']
    start=[int(r['clock']) for r in trace if r['event']=='ppu_dma']
    last=[int(r['clock']) for r in trace if r['event']=='ppu_last']
    dma=[r for r in samples if r['event']=='dma']
    assert [r['clock'] for r in dma]==start and len(last)==len(dma)
    assert all(0<=r['h']<1364 for r in samples)
    raw_start=0
    for i,r in enumerate(dma):
        assert start[i]<last[i]
        dst=r['dst']
        bg,obj,raw,map_base=(0xc000,0x8000,0x9000,0xa000) if r['bank'] else (0,0x4000,0x5000,0x6000)
        if r['port'] in (4,0x22):
            assert r['clock']>latch['clock']
            r['kind']='OAM' if r['port']==4 else 'CGRAM'
        else:
            assert r['port']==0x18 and r['clock']<latch['clock']
            r['kind']=next(name for name,base,length in [('map',map_base,4096),('BG',bg,16384),('OBJ',obj,4096),('raw',raw,2048)] if base<=dst<base+length)
            # Non-interlaced NTSC has a 1360-clock line 240 on odd frames.
            nominal=(latch['line']-r['line'])*1364+latch['h']-r['h']
            frame=int(next(ev['frame'] for ev in trace if ev['event']=='ppu_dma' and int(ev['clock'])==r['clock']))
            short_line=4 if r['line']<=240<latch['line'] and frame%2==0 else 0
            assert latch['clock']-r['clock']==nominal-short_line
            if r['kind']=='raw' and not raw_start:
                raw_start=r['clock']
        r['to_last_write']=last[i]-start[i]
        if start[i]<latch['clock']:
            following=min(latch['clock'],start[i+1])
            r['after_last_to_next_or_latch']=following-last[i]
            assert r['after_last_to_next_or_latch']>=0
    totals=Counter()
    for r in dma:
        totals[r['kind']]+=r['bytes']
    assert totals['OAM']==544 and totals['CGRAM']==512 and raw_start
    return dict(dma=dma,bytes=dict(totals),latch_line=latch['line'],latch_h=latch['h'],
                clocks_past_start_of_line247=(latch['line']-247)*1364+latch['h'],
                first_raw_to_latch=latch['clock']-raw_start)


def quiet_maps(folder):
    events=read(folder/'events.json')
    obj=read(folder/'obj-phases.json')
    rows=[]
    for g in range(905,958):
        es=[e for e in events if e['generation']==g]
        def clock(event):
            v,=[e['clock'] for e in es if e['event']==event]
            return v
        end=clock('end_enter')
        begin=clock('source_begin')
        cutoff=obj[str(g)]['end_accepted']
        quiet=[e for e in es if e['event']=='map_packet_enter' and end<=e['clock']<cutoff]
        assert all(e['early'] for e in quiet)
        offsets=[e['offset'] for e in quiet]
        assert offsets==sorted(set(offsets))
        spi=[e for e in es if e['event']=='SPI' and end<=e['start']<cutoff]
        wire=[e for e in spi if e['opcode']=='0xe1' and e['packet_opcode'] in (2,4)]
        assert len(wire)==len(quiet)
        for q in quiet:
            prior=[e for e in spi if e['clock']<=q['clock']]
            assert prior[-1]['opcode']=='0xe8'
        rows.append(dict(g=g,quiet_offsets=offsets,quiet_wire_B=sum(e['bytes'] for e in wire),
                         end_wait_ms=ms(cutoff-end),last_OBJ_from_source_ms=ms(obj[str(g)]['last_obj_rom_response']-begin)
                         if obj[str(g)].get('last_obj_rom_response') is not None else None))
    return rows


def packet_content(folder):
    packets=Counter()
    maps=[]
    for line in (folder/'packets.jsonl').read_text().splitlines():
        _,_,head,payload=json.loads(line)
        b=bytes.fromhex(head)
        identity=b[:2]+b[4:]  # Skip only the sequence assigned by the queue owner.
        packets[identity,payload]+=1
        if b[0] in (2,4) and b[1]==2:
            maps.append(identity)
    return packets,maps


def raw_changes(folder,g):
    # Same two-bank rotation, after both prior frames passed their final ACK.
    begins={}
    for line in (folder/'packets.jsonl').read_text().splitlines():
        b=bytes.fromhex(json.loads(line)[2])
        if b[0]==1:
            begins[int.from_bytes(b[8:10],'little')]=int.from_bytes(b[4:8],'little')
    assert begins[g]==begins[g-2]+2
    a,b=[(folder/f'expected-{generation}.bin').read_bytes()[1121:3169] for generation in (g-2,g)]
    assert len(a)==len(b)==2048
    changed=[]
    for pair in range(3):
        for row in (0,1):
            offsets=[t*64+pair*16+row*2+byte for t in range(32) for byte in (0,1)]
            changed.append(sum(a[k]!=b[k] for k in offsets))
    assert sum(changed)==sum(x!=y for x,y in zip(a,b))
    return changed


def analyze(a):
    prior=read(ROOT/'analysis/map527-verification.json')
    control=read(ROOT/'analysis/map526-verification.json')
    reference=read(ROOT/'analysis/prefix523-verification.json')
    plans={r['generation']:r for r in read(ROOT/'analysis/obj518-verification.json')['plans']['frames']}
    oracle=tiles(a.fixture,957)
    firmware=a.arm/'obj-nes-100/firmware.stm'
    sz=[int(x) for x in (a.arm.parent/'size.log').read_text().splitlines()[-1].split()[:3]]
    guards=read(a.guards)
    assert guards['firmware']==sha(firmware) and len(guards['rows'])==9
    responses=read(a.responses)
    assert responses['passed'] and responses['cases']==40 and responses['candidate_SHA256']==sha(firmware)
    assert sha(a.sof)==prior['unchanged_FPGA']
    phases=[]
    for i,(base,replay,new,check) in enumerate(zip(a.base,a.replay,a.new,a.check)):
        audit=read(replay/'audit.json')
        ref=prior['phases'][i]['variants']['frontier']
        assert sha(base/'window.csv')==audit['trace']==ref['pins']['window.csv'] and audit['frames']==53
        kwargs=reference['phases'][i]['candidate']
        def cost(path,fw):
            return run_cost(path,'row254',dict(kwargs,firmware=fw),plans,Calendar(a.calendar),oracle)
        old,keys=cost(base,prior['builds']['frontier']['sha256'])
        s,new_keys=cost(new,sha(firmware))
        checked=read(check/'audit.json')
        assert checked['frames']==53 and checked['trace']==s['pins']['window.csv']
        assert sha(check/'seal528.csv')==sha(new/'seal528.csv')
        assert old['pins']==ref['pins'] and s['client']==old['client'] and keys==new_keys
        assert packet_content(base)==packet_content(new)
        assert old['dma_B']==s['dma_B'] and old['ROM_reads']==s['ROM_reads']
        assert not (new/'callback-error.txt').exists()
        assert all(sha(base/f'frame-{g}.rgb')==sha(new/f'frame-{g}.rgb') for g in range(905,958))
        q=quiet_maps(new)
        original=quiet_maps(base)
        assert all(not r['quiet_offsets'] for r in original)
        targets={}
        for g in (952,954):
            n=g-905
            b,v=seal(replay,g),seal(new,g)
            for record,frame in [(b,old['frames'][n]),(v,s['frames'][n])]:
                assert sum(record['bytes'].values())-1056==frame['pre_final_PPU_B']
            targets[g]=dict(baseline=b,candidate=v,base_frame=old['frames'][n],candidate_frame=s['frames'][n],
                            baseline_ARM=original[n],candidate_ARM=q[n],bytes_changed_per_raw_job=raw_changes(new,g))
        s.pop('frames')
        physical=control['phases'][i]['variants']['524']
        phases.append(dict(start=prior['phases'][i]['start'],cost=s,targets=targets,
                           publication_frames=sum(bool(r['quiet_offsets']) for r in q),
                           publication_packets=sum(len(r['quiet_offsets']) for r in q),
                           final_vs527_ms=ms(s['final_ack']-old['final_ack']),final_vs524_ms=ms(s['final_ack']-physical['final_ack']),
                           dense_vs527_ms=s['dense_ms']-old['dense_ms'],dense_vs524_ms=s['dense_ms']-physical['dense_ms'],
                           base_independent_replay=audit,candidate_independent_replay=checked))
    return dict(phases=phases,firmware_SHA256=sha(firmware),Flash_B=firmware.stat().st_size,BSS=sz[2],guards=guards,
                unchanged_SOF=sha(a.sof),response_cases=responses['cases'],physical_trial=False)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for field in ('base','replay','new','check'):
        p.add_argument('--'+field,nargs=2,required=True,type=Path)
    for field in ('fixture','arm','calendar','guards','responses','sof','out'):
        p.add_argument('--'+field,required=True,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',encoding='utf8',newline='\n')
