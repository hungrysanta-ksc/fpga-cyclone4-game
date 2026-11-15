# SPDX-License-Identifier: MIT
"""Relate ARM commitment, SPI, CPU acceptance and display to the target 969 VBlank."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_nes_output768 import csv_groups, one, read, sha
from analyze_nes_tail735 import section5
from test_nes_raw506_joint import MASTER


def ms(t):
    return round(1000*t/MASTER,6)


def measure(d, baseline):
    j=read(d/'joint.json')
    assert j['passed'] and j['commits']==j['map_WRAM_VRAM_verified']==66
    old=read(baseline/'joint.json')
    assert j['parameters']==old['parameters'] and j['client_SHA256']==old['client_SHA256']
    for g in range(905,971):
        for name in (f'frame-{g}.rgb',f'map-{g}.bin',f'expected-{g}.bin'):
            assert sha(d/name)==sha(baseline/name)
    assert section5(d)==section5(baseline)
    w=csv_groups(d/'window.csv')
    def mark(g,k):
        return one([r for r in w[g] if r['op']==3],k)
    e=[r for r in read(d/'events.json') if r.get('generation')==969]
    prepared=one(e,'prepared777')
    seal=mark(969,'load')
    output=one(e,'output_enter531')['clock']
    dma=[r for r in w[969] if r['event']=='ppu_dma' and output<r['clock']<seal['clock']]
    # Define the common target by the previous display's frame, even if the
    # candidate moves the first DMA or never starts it in this VBlank.
    actual=mark(969,'reveal')['frame']
    target=mark(968,'reveal')['frame']+2
    anchor=next(r for r in reversed(csv_groups(d/'seal528.csv')[969]) if r['event']=='dma' and r['port']==4)
    assert any(r['event']=='ppu_dma' and r['clock']==anchor['clock'] and r['frame']==actual for r in w[969])
    begin=anchor['clock']-(anchor['line']-225)*1364-anchor['h']+4*(actual%2==0 and anchor['line']>240)
    for frame in range(actual-1,target-1,-1):
        begin-=262*1364-4*(frame%2==0)
    assert actual>=target
    cutoff=begin+22*1364-4*(target%2==0)
    line227=begin+2*1364
    spi=[r for r in e if r.get('opcode')=='0xe1']
    rows=[]
    packets=[json.loads(line) for line in (d/'packets.jsonl').read_text().splitlines()]
    accepted=[r for r in w[969] if r['event']=='load']
    for r,tx in zip(accepted,spi,strict=True):
        _,t,head,_=packets[r['index']-1]
        h=bytes.fromhex(head)
        op,sec=h[:2]
        off=int.from_bytes(h[10:12],'little')
        assert (op,sec)==(r['op'],r['section']) and h[8:10]==(969).to_bytes(2,'little')
        assert abs(t-tx['clock'])<=1 and t<=r['clock']
        ack=one([a for a in w[969] if a['index']==r['index']],'ack')['clock']
        kind=('OAM' if op==9 else 'scroll' if sec==5 and off==0 else
              'padding' if sec==5 and off==21 else 'table' if sec==5 and len(h)==256 else
              'map' if sec==2 else 'OBJ' if op==7 and sec==1 else 'other')
        if kind in ('OAM','scroll','table'):
            field={'OAM':'oam','scroll':'scroll','table':'table'}[kind]
            payload=h[16:128] if op==9 else h[16:]
            assert hashlib.sha256(payload).hexdigest()==prepared['fields'][field]['sha256']
        credits=[v for v in e if v.get('opcode')=='0xe0' and v['clock']<=tx['start']]
        status=bytes.fromhex(credits[-1]['reply']) if credits else b''
        depth=sum(previous['ack']>tx['start'] for previous in rows)
        assert depth<4
        rows.append(dict(unretired_at_E1_start=depth,
                         last_E0=None if not credits else dict(clock=credits[-1]['clock'],flags=status[2],
                             sent=int.from_bytes(status[3:5],'big'),retired=int.from_bytes(status[5:7],'big')),
                         kind=kind,op=op,section=sec,offset=off,wire=tx['bytes'],seq=int.from_bytes(h[2:4],'little'),
                         start=tx['start'],end=tx['clock'],load=r['clock'],ack=ack))
    # Preserve map, tile token and ordinary payload identity independently of packet order.
    def content(ps):
        result=[]
        for _,_,header,tile in ps:
            h=bytes.fromhex(header)
            if h[8:10]==(969).to_bytes(2,'little'):
                result.append((h[:2]+h[4:],tile))
        return sorted(result)
    assert content(packets)==content([json.loads(x) for x in (baseline/'packets.jsonl').read_text().splitlines()])
    idle=[r for r in w[969] if r['event']=='idle524' and output<r['clock']<seal['clock']]
    tiles={r['clock']:r for r in csv_groups(d/'tile532.csv').get(969,[]) if r['event']=='tile'}
    assert len(idle)==len(dma)
    previous_cutoff=cutoff-(262*1364-4*(target%2==0))
    ready_map=[]
    for r in rows:
        if r['kind']!='map':continue
        ready_map.append(dict(offset=r['offset'],ACK_vs_first_end246_ms=ms(r['ack']-previous_cutoff),
                              E1_start_vs_first_end246_ms=ms(r['start']-previous_cutoff)))
    transfers=[]
    for offer,x in zip(idle,dma):
        assert 0<=x['clock']-offer['clock']<1000
        if offer['value']>=65536:
            source=['map',offer['value']-65536,x['value']]
        else:
            tile=tiles[offer['clock']]
            source=['tile',tile['dst'],x['value']]
        transfers.append(source)
    ends=[r for r in w[969] if r['event']=='ppu_last' and output<r['clock']<seal['clock']]
    assert len(ends)==len(dma)
    validate=mark(969,'upload165_entry')['clock']-seal['clock']
    after=ms(cutoff-ends[-1]['clock']) if ends else None
    def early(r):
        return r['kind'] in ('OAM','scroll','padding','table') or r['section']==5
    assert {r['kind'] for r in rows}>={'OAM','scroll','padding','table'}
    ref_w=csv_groups(baseline/'window.csv')
    phase_slips={}
    old_delta=0
    for g in range(905,971):
        ref_show=one([r for r in ref_w[g] if r['op']==3],'reveal')
        delta=mark(g,'reveal')['frame']-ref_show['frame']
        if delta!=old_delta:phase_slips[g]=delta-old_delta
        old_delta=delta
    return dict(phase_slips_vs_767=phase_slips,ACK968=seal_ack(w,968),
                ACK968_to_969_ms=ms(seal_ack(w,969)-seal_ack(w,968)),
                map_acceptance=ready_map,early_transfers=transfers,SEAL_to_upload_ms=ms(validate),
                last_pre_DMA_to_end246_ms=after,prepared=prepared,
                post_SEAL_bytes=sum(r['value'] for r in w[969] if r['event']=='ppu_dma' and r['clock']>seal['clock']),output=output,beam227=line227,close246=cutoff,
                packets=rows,ACK969=seal_ack(w,969),ACK970=seal_ack(w,970),
                prepared_to_line227_ms=ms(line227-prepared['clock']),
                early_ordinary_issued_B=sum(r['wire'] for r in rows if early(r) and r['end']<=line227),
                early_ordinary_loaded_B=sum(r['wire'] for r in rows if early(r) and r['load']<=line227),
                early_ordinary_acked_B=sum(r['wire'] for r in rows if early(r) and r['ack']<=line227),
                remaining_E1_B=sum(r['wire'] for r in rows if r['start']>=line227),
                display_VB=actual-target+2,pre_DMAs=[(r['value'],r['frame']-target,r['line']) for r in dma],
                pre_DMA_B=sum(r['value'] for r in dma),seal_vs_end246_ms=ms(seal['clock']-cutoff),
                mean952_957_ms=ms((mark(957,'reveal')['clock']-mark(951,'reveal')['clock'])/6),
                start=j['parameters']['start'],firmware=j['firmware_SHA256'],client=j['client_SHA256'],
                verified_frames=j['commits'],events=sha(d/'events.json'))


def seal_ack(w,g):
    return one([r for r in w[g] if r['op']==3],'ack')['clock']


def run(t,work):
    result={'phases':{},'builds':{},'table_first_rejection':read(t/'nes-prefix777-table02/proof.json'),
            'prefix_STOP':read(t/'nes-prefix777-stop02/proof.json')}
    for p in (1,2):
        baseline=t/f'nes-cost768-767-p{p}-ext'
        result.setdefault('fixed_arrivals',{})[p]=read(t/f'nes-prefix777-fixed02-p{p}'/'audit.json')
        variants=result['phases'][p]={}
        for name in ('ref','issue','section'):
            d=t/f'nes-prefix777-{name}02-p{p}'
            r=variants[name]=measure(d,baseline)
            if name=='ref':
                assert read(d/'joint.json')['frames']==read(baseline/'joint.json')['frames']
                assert sha(d/'window.csv')==sha(baseline/'window.csv') and sha(d/'packets.jsonl')==sha(baseline/'packets.jsonl')
            ref=variants['ref']
            r['includes_767_transfers_in_order']=all(
                x in r['early_transfers'] for x in ref['early_transfers']) and (
                [x for x in r['early_transfers'] if x in ref['early_transfers']]==ref['early_transfers'])
            r['delta_from_767']={k:round(r[k]-ref[k],6) for k in ('pre_DMA_B','mean952_957_ms','ACK969','ACK970')}
            r['accept_vs_227_ms']={row['kind']:ms(row['load']-r['beam227']) for row in r['packets'] if row['kind'] in ('OAM','scroll','padding','table')}
            r['last_write_vs_227_ms']={k:ms(v['last_write']-r['beam227']) for k,v in r['prepared']['fields'].items() if v['last_write'] is not None}
    for name,folder,guard in [('issue','arm01','guards.json'),('section','arm02','guardsB.json')]:
        arm=work/folder/'src/obj-nes-100'
        guards=read(work/guard)
        assert sha(arm/'firmware.stm')==guards['firmware']==result['phases'][1][name]['firmware']==result['phases'][2][name]['firmware']
        result['builds'][name]=dict(firmware_B=(arm/'firmware.stm').stat().st_size,ELF=sha(arm/'sd2snes.elf'),
                                    guards=guards,size=(work/folder/'size.log').read_text().splitlines()[-1].split()[:3])
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('temp','work','output'):p.add_argument(arg,type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(run(a.temp,a.work),indent=2)+'\n',encoding='utf8')
