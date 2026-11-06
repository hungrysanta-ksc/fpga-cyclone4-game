# SPDX-License-Identifier: MIT
"""Normalize every output packet, then compare display and receipt clocks at matched work."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from analyze_nes_map626 import csv_groups,ms,one,packets,read,sha


def normalize(folder):
    cpu=csv_groups(folder/'window.csv')
    beam=csv_groups(folder/'seal528.csv')
    last={}
    work={}
    counts={}
    for g,commands in packets(folder).items():
        bank=one(beam[g],'final_credit')['bank']
        prior_serial,prior=last.get(bank,(0,bytes(4096)))
        image=bytearray(prior)
        target=(folder/f'map-{g}.bin').read_bytes()
        rows=set()
        body=Counter()
        compressed=[]
        map_e1=0
        accepted=one([r for r in cpu[g] if r['op']==3],'ack')
        assert accepted['value']==1 and accepted['clock']>commands[-1][2]
        seq=0
        for h,tile,_ in commands:
            op,sec,serial,gen,off,n,span=(*h[:2],*struct.unpack_from('<I4H',h,4))
            assert gen==g and int.from_bytes(h[2:4],'little')==seq and len(h)==n+16
            seq+=1
            if sec!=2:
                key=(op,sec,off,span,tile) if op==7 else (op,sec,off,span,h[16:])
                body[key]+=1
                continue
            map_e1+=len(h)+3
            raw=h[16:]
            if op==9:
                base,s1,s2=struct.unpack_from('<IHH',raw)
                assert prior_serial and base==prior_serial==serial-2
                assert 2048<=off and span in (64,128,192) and off+span<=4096
                mask=int.from_bytes(raw[8:8+span//32],'little')
                pos=8+span//32
                for i in range(0,span,4):
                    changed=prior[off+i:off+i+4]!=target[off+i:off+i+4]
                    assert changed==bool(mask & (1<<(i//4)))
                    if changed:
                        assert pos+4<=len(raw)
                        image[off+i:off+i+4]=raw[pos:pos+4]
                        pos+=4
                assert pos==len(raw)<span
                a=b=0
                for w, in struct.iter_unpack('<H',image[off:off+span]):
                    a=(a+w)&65535
                    b=(b+a)&65535
                assert (a,b)==(s1,s2)
                compressed.append(dict(offset=off,expanded=span,wire_B=len(h)+3,changed=mask.bit_count()))
            else:
                assert op in (2,4,5)
                if op!=2:raw*=span//2
                span=len(raw)
                image[off:off+span]=raw
            assert span%64==off%64==0
            touched=set(range(off,off+span,64))
            assert not rows.intersection(touched)
            rows.update(touched)
        assert image==target and (prior_serial or len(rows)==64)
        last[bank]=(serial,bytes(image))
        counts[g]=dict(map_wire=map_e1,deltas=compressed,bank=bank)
        work[g]=(body,sorted(rows))
    return work,counts


def measure(d):
    ev=read(d/'events.json')
    cpu=csv_groups(d/'window.csv')
    show={}
    for g in range(905,958):
        seal=[r for r in cpu[g] if r['op']==3]
        show[g]=one(seal,'reveal')
        assert show[g]['frame']==one(seal,'ack')['frame'] and 225<=show[g]['line']<262
    stream=[e for e in ev if e['generation']==951]
    spi=[e for e in stream if e['event']=='SPI']
    frozen=one(stream,'bg_map_frozen')['clock']
    prep=one(stream,'prepare_enter')['clock']
    sends=[e for e in spi if e['opcode']=='0xe1']
    cpu_seal=[r for r in cpu[951] if r['op']==3]
    idx=one(cpu_seal,'load')['index']-len(sends)+1
    trace=[]
    for k,((h,_,p),e) in enumerate(zip(packets(d)[951],sends,strict=True)):
        assert abs(p-e['clock'])<=1
        if h[1]==2:
            consumed=[r for r in cpu[951] if r['index']==idx+k]
            head=one(consumed,'load')['clock'];ack=one(consumed,'ack')['clock']
            assert p<=head<=ack
            trace.append(dict(offset=int.from_bytes(h[10:12],'little'),op=h[0],B=e['bytes'],
                        early=frozen<=e['start']<prep,issue=e['start'],push=p,head=head,ack=ack))
    target_frame=show[950]['frame']+3
    anchor=next(r for r in reversed(csv_groups(d/'seal528.csv')[951]) if r['event']=='dma' and r['port']==4)
    frame=show[951]['frame']
    assert any(r['event']=='ppu_dma' and r['clock']==anchor['clock'] and r['frame']==frame for r in cpu_seal)
    start=anchor['clock']-(anchor['line']-225)*1364-anchor['h']+(4 if frame%2==0 and anchor['line']>240 else 0)
    while frame>target_frame:
        frame-=1
        start-=262*1364-(4 if frame%2==0 else 0)
    while frame<target_frame:
        start+=262*1364-(4 if frame%2==0 else 0)
        frame+=1
    cutoff=start+22*1364-(4 if frame%2==0 else 0)
    last=[r for r in cpu[957] if r['op']==3]
    final=one(last,'final212')['clock']
    return dict(intervals={g:show[g]['frame']-show[g-1]['frame'] for g in range(951,958)},
                dense_VB=show[955]['frame']-show[950]['frame'],dense_ms=ms(show[955]['clock']-show[950]['clock']),
                display922=show[922]['frame'],display950=show[950]['frame'],display951=show[951]['frame'],
                ACK=one(last,'ack')['clock'],wait957=sum(r['event']=='wait169' and r['clock']>=final for r in last),
                bg_to_prep_ms=ms(prep-frozen),early_SPI=[[e['opcode'],e['bytes']] for e in spi if frozen<=e['start']<prep],
                early_credit_depths=[e['outstanding'] for e in stream if e['event']=='map_credit_attempt' and frozen<=e['clock']<prep],
                prep_from_prev_display_ms=ms(prep-show[950]['clock']),E1_951=sum(e['bytes'] for e in sends),
                SPI_951=sum(e['bytes'] for e in spi),E0_polls_951=sum(e['opcode']=='0xe0' for e in spi),
                SEAL_from_target_cutoff_ms=ms(sends[-1]['start']-cutoff),
                map_tx_ms=sum(ms(e['clock']-e['start']) for e,(p,_,_) in zip(sends,packets(d)[951]) if p[1]==2),
                post_ACK_to_ARM_return_ms=ms(one(stream,'output_return531')['clock']-one(cpu_seal,'ack')['clock']),
                SEAL_from_prev_display_ms=ms(sends[-1]['start']-show[950]['clock']),map_trace951=trace,
                map_head_service_ms=sum(ms(row['ack']-row['head']) for row in trace),
                ROM923=read(d/'obj-phases.json')['923']['cache611'][0][4])


def compare(a):
    old=read(Path(__file__).resolve().parents[1]/'analysis/tail627-verification.json')
    roots={'base':'nes-seal625-tables-bg','control':'nes-map628-control','front':'nes-map628-front',
           'front3b':'nes-map628-front3b','checked':'nes-map628-checked'}
    programs=dict(base=a.build.parent/'nes-seal625/tables-bg',control=a.build.parent/'nes-tail627/control',
                  **{n:a.build/n for n in ('front','front3b','checked')})
    result=dict(phases=[],Flash={k:(p/'src/obj-nes-100/firmware.stm').stat().st_size for k,p in programs.items()})
    for i in (1,2):
        ref=a.traces/f'{roots["base"]}-{i}'
        j=read(ref/'joint.json')
        refwork=normalize(ref)[0]
        phase={}
        for m,stem in roots.items():
            d=a.traces/f'{stem}-{i}'
            joint=read(d/'joint.json')
            assert joint['passed'] and joint['commits']==53 and joint['last_status']==1
            assert all(j[k]==joint[k] for k in ('parameters','vram_DMA_B','ROM_read_allocations'))
            assert joint['firmware_SHA256']==sha(programs[m]/'src/obj-nes-100/firmware.stm')
            assert joint['client_SHA256']==(sha(a.build/'client/sink165.sfc') if m=='checked' else j['client_SHA256'])
            work,count=normalize(d)
            assert work==refwork
            assert all(sha(d/f)==sha(ref/f) for g in range(905,958) for f in (f'frame-{g}.rgb',f'map-{g}.bin'))
            r=measure(d)
            if m in ('base','control'):
                prior=old['phases'][i-1][m]
                assert r['ACK']==prior['ACK'] and r['dense_VB']==prior['dense']
                if m=='control':
                    original=a.traces/f'nes-tail627-control-{i}'
                    assert all(sha(d/n)==sha(original/n) for n in ('packets.jsonl','window.csv'))
            r.update(frame951=count[951],all_delta_packets=sum(len(v['deltas']) for v in count.values()),
                     wire=joint['wire_B'],irq=joint['SysTick_calls'],max_banks=joint['max_bulk_banks'],
                     workspace_end=joint['workspace_end'],lowest_stack=joint['observed_stack_low'],
                     pins={f:sha(d/f) for f in ('events.json','joint.json','packets.jsonl','window.csv','seal528.csv')})
            phase[m]=r
        for r in phase.values():
            r['ACK_delta_ms']=ms(r['ACK']-phase['base']['ACK'])
            r['ROM923_delta_ms']=ms(r['ROM923']-phase['base']['ROM923'])
            r['joint_improvement']=all((r['intervals'][951]<=3,r['dense_VB']<phase['base']['dense_VB'],
                                        r['ACK_delta_ms']<0,r['wait957']==0))
        result['phases'].append(phase)
    guard_dir=a.traces/'nes-map628-guards04'
    result['consumer_guards']=read(guard_dir/'result.json')
    guards=result['consumer_guards']
    assert {r['boundary']:r['status'] for r in guards['guards']}=={
        **dict.fromkeys(('cold','identity','checksum','trailing','short','retained'),0xe0),'stop':0xe4}
    assert guards['restart']==dict(commits=2,status=1,restored_map_bytes=16384)
    for r in guards['guards']:
        run=guard_dir/f"{r['generation']}-{r['boundary']}"
        assert sha(run/'client.sfc')==sha(a.build/'client/sink165.sfc')
    result['ARM_guards']=read(a.build/'checked/guards.json')
    assert result['ARM_guards']['firmware']==sha(programs['checked']/'src/obj-nes-100/firmware.stm')
    result['early_edges']=read(a.traces/'nes-map628-test_nes_map616_edges/edges.json')
    result['early_STOP']=read(a.traces/'nes-map628-check_nes_tail627_stop/result.json')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','build','out'):
        p.add_argument('--'+k,type=Path,required=True)
    compare(p.parse_args())
