# SPDX-License-Identifier: MIT
"""Bind the last staged OBJ, its E8 response, E1, SNES receipt and VRAM write to one token."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_owner739 import packets, csv_groups, ms, read, sha
from analyze_nes_receipt742 import whole
from analyze_nes_beam741 import records
from analyze_nes_game215 import crc8


def timing(folder, base, owner, dma):
    r=whole(folder,base)
    rows=csv_groups(folder/'window.csv')
    cpu=rows[957]
    reveals={g:next(row for row in rows[g] if row['op']==3 and row['event']=='reveal') for g in (951,956,957)}
    seal=next(e['clock'] for e in cpu if e['op']==3 and e['event']=='load')
    head=packets(folder)[957]
    idx=max(i for i,(h,_,_) in enumerate(head) if h[:2]==bytes((7,1)))
    h,payload,push=head[idx]
    token=int.from_bytes(h[16:20],'little')
    descriptor=bytes((1,1))+h[14:16]+h[10:12]+h[8:10]+h[16:20]
    assert len(payload)==int.from_bytes(h[14:16],'little')==288
    events=[e for e in read(folder/'events.json') if e.get('generation')==957]
    spi=[e for e in events if e['event']=='SPI']
    query=next(e for e in spi if e['opcode']=='0xe8' and bytes.fromhex(e['reply'])[6:18]==descriptor)
    raw=bytes.fromhex(query['reply'])
    assert raw[1:3]==bytes((0xd7,4)) and raw[18]==0 and raw[19]==crc8(raw[1:19])
    submit=next(e for e in spi if e['opcode']=='0xe1' and abs(e['clock']-push)<1)
    call=next(e for e in events if e['event']=='call673' and e.get('op')==23 and e['section']==1 and e['offset']==2720)
    wire=next(e for e in events if e['event']=='wire664' and e['section']==1 and e['offset']==2720)
    producer=read(folder/'obj-phases.json')['957']
    end=producer['banks557'][-1]
    assert end['decoded']==end['count'] and end['seal']==producer['end_accepted']
    taps=records(owner/'owner.csv')
    assert read(owner/'audit.json')['matched_events']==sum(map(len,rows.values()))
    def returned(value):
        return next(e['clock'] for e in taps if e['event']=='bank_release' and e['value']==value)
    loads=[e for e in cpu if e['event']=='load']
    acks=[e for e in cpu if e['event']=='ack']
    assert len(loads)==len(acks)==len(head)
    receipt=acks[idx]
    ticks=dict(last_OBJ_ROM=producer['last_obj_rom_response'],descriptor_staged=end['release']+1,
               previous_BG_return=returned(token-1),E8_start=query['start'],E8_end=query['clock'],
               ARM_submit_checked=call['clock'],ARM_enqueue=wire['clock'],E1_start=submit['start'],
               E1_complete=push,SNES_load=loads[idx]['clock'],OBJ_bank_return=returned(token),
               SNES_receipt=receipt['clock'],last_map_ACK=r['map_last_ACK'],SEAL=seal)
    ready=max(ticks['previous_BG_return'],ticks['descriptor_staged'])
    assert ticks['last_OBJ_ROM']<=ticks['descriptor_staged']
    assert ready<=ticks['E8_start']<ticks['E8_end']<=ticks['ARM_submit_checked']<=ticks['ARM_enqueue']
    assert ticks['ARM_enqueue']<=ticks['E1_start']<push<=ticks['SNES_load']<ticks['OBJ_bank_return']<=receipt['clock']
    obj_dma=[d for d in records(dma/'dma748.csv') if d['g']==957 and d['source']==19104]
    assert sum(d['bytes'] for d in obj_dma)==288
    map_dma={}
    for g,src in ((952,55296),(957,22528)):
        boundary=next(e['clock'] for e in rows[g] if e['op']==3 and e['event']=='load')
        map_dma[g]=[d for d in records(dma/'dma748.csv') if d['g']==g and d['source']==src
                    and d['bytes']==1536 and d['clock']<boundary]
        assert bool(map_dma[g])==r['long_map'][g]
    focus=map_dma[957]
    margin=focus[0]['clock']-receipt['clock'] if focus else None
    if focus:
        ticks['map1536_start']=focus[0]['clock']
        ticks['map1536_last']=next(e['clock'] for e in cpu if e['event']=='ppu_last' and e['clock']>focus[0]['clock'])
    deadline=False
    if focus:
        first=focus[0]
        start=first['clock']-(first['line']-225)*1364-first['h']
        deadline=any(start<=d['clock']<start+33*1364 and d['line']<=257 and d['clock']<seal for d in obj_dma)
    return dict(ticks=ticks,ms_since_previous_display={k:ms(v-reveals[956]['clock']) for k,v in ticks.items()},
                E8_reply=raw.hex(),token=token,ready_to_E8_ms=ms(ticks['E8_start']-ready),
                ARM_credit_at_submit=call['sent']-call['retired'],map_pushes_before_OBJ=sum(h[1]==2 for h,b,t in head[:idx]),
                map_pushes_after_OBJ=sum(h[1]==2 for h,b,t in head[idx+1:]),map_DMA=map_dma,OBJ_DMA=obj_dma,
                OBJ_receipt_line=receipt['line'],OBJ_receipt_margin=margin,OBJ_by257=deadline,
                guards=dict(line951=r['public951'],final_wait957=r['final_wait957'],intervals=r['intervals']),
                dense_ms=r['dense_ms'],dense_delta_us=r['dense_delta_us'],ACK=r['final_ACK'],ACK_delta_us=r['ACK_delta_us'],
                firmware=r['firmware'],ARM_instructions=r['ARM_instructions'],wire_B=r['wire_B'],ROM_reads=r['ROM_reads'],
                pins={**r['pins'],'owner':sha(owner/'owner.csv'),'DMA':sha(dma/'dma748.csv'),
                      'producer':sha(folder/'obj-phases.json')})


def analyze(a):
    result=dict(stage=749,reference=727,board='707D',ROM=694,phases={},ARM={})
    for k in ('early','notice','page'):
        build=a.probe/k
        fw=build/'src/obj-nes-100/firmware.stm'
        result['ARM'][k]=dict(size=fw.stat().st_size,free=212992-fw.stat().st_size,sha=sha(fw),
                              sections=(build/'size.log').read_text().splitlines()[-1].split()[:3])
        for g in ('menu533','deadline719','receipt742'):
            guard=read(a.probe/f'{k}-{g}.json')
            assert guard['firmware']==sha(fw)
            result['ARM'][k][g]=guard
    direct=read(a.probe/'page-direct.json')
    assert direct['firmware']==result['ARM']['page']['sha'] and len(direct['rows'])==8
    result['ARM']['page']['handoff']=direct['rows']
    for n in (1,2):
        base=a.temp/f'nes-pair727-a{n}'
        phase=result['phases'][n]={}
        for k in ('ref','early','notice','page'):
            d=base if k=='ref' else a.temp/f'nes-obj749-{k}{n}'
            obs=a.temp/(f'nes-owner739-ref{n}-trace' if k=='ref' else f'nes-obj749-{k}{n}-trace')
            dma=a.temp/f'nes-input748-ref{n}-decision' if k=='ref' else d
            r=phase[k]=timing(d,base,obs,dma)
            if k!='ref':assert r['firmware']==result['ARM'][k]['sha']
            r['ACK_delta_clocks']=r['ACK']-phase['ref']['ACK']
            offset=r['ms_since_previous_display']
            r['receipt_margin_to_ref_map_ms']=phase['ref']['ms_since_previous_display']['map1536_start']-offset['SNES_receipt']
            r['meets']=bool(r['map_DMA'][952] and r['map_DMA'][957] and r['OBJ_receipt_margin']>0 and r['OBJ_by257']
                            and r['guards']['line951']<=246 and r['guards']['final_wait957']==0
                            and all(r['guards']['intervals'][g]<=v for g,v in ((908,2),(911,2),(952,3)))
                            and r['dense_delta_us']<0 and r['ACK_delta_clocks']<0)
        # Re-run the actual 694 instructions with STOP, corrupt identity and a new queue head.
        for k in ('early','page'):
            target=a.temp/f'nes-obj749-{k}{n}'
            fault={}
            for mode in ('stop','stale'):
                d=a.temp/f'{target.name}-{mode}'
                j=read(d/'result.json')
                assert j['passed'] and j['commits']==52 and j['last_status'] in ((0,228) if mode=='stop' else (224,))
                assert sha(d/'retained.rgb')==sha(target/'frame-956.rgb')
                fault[mode]=dict(commits=j['commits'],status=j['last_status'],retained_RGB=sha(d/'retained.rgb'))
            d=a.temp/f'{target.name}-head'
            edge,idx,op,sec=map(int,(d/'head748.txt').read_text().split())
            events=csv_groups(d/'window.csv')[957]
            first=next(e for e in events if e['clock']>edge and e['event'] in ('load','ppu_dma'))
            assert (first['event'],first['index'],first['op'],first['section'])==('load',idx,op,sec)
            assert read(d/'result.json')['commits']==53
            fault['new_head']=dict(edge=edge,next_load=first['clock'],op=op,section=sec)
            phase[k]['receiver_guards']=fault
            q=a.temp/f'{target.name}-queue'
            assert read(q/'audit.json')['matched_events']==sum(len(v) for v in csv_groups(target/'window.csv').values())
            with (q/'queue749.csv').open() as f:
                log=list(csv.DictReader(f))
            dma=next(row for row in log if row['path']=='MDMAEN')
            assert int(dma['clock'])==phase[k]['ticks']['map1536_start']
            after=[row for row in log if row['path']=='selected526']
            assert after and all(row['descriptors']=='0840:48 4AA0:288' for row in after)
            phase[k]['queue_at_map']=dma['descriptors']
            phase[k]['after_map']=dict(first_selected_line=int(after[0]['line']),last_selected_line=int(after[-1]['line']),
                                       descriptors=after[0]['descriptors'],first_occupancy=int(after[0]['occupancy']),
                                       first_defer=next(int(row['line']) for row in log if row['path']=='defer_beam'),
                                       tap=sha(q/'queue749.csv'))
    result['passing']=[k for k in ('early','notice','page') if all(result['phases'][n][k]['meets'] for n in (1,2))]
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
