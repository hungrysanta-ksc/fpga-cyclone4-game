# SPDX-License-Identifier: MIT
"""Reconcile causal map milestones, ROM supply and actual display intervals."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_map526 import ROOT,Calendar,read,run_cost,ms,sha,tiles


def first_maps(folder,summary):
    events=read(folder/'events.json')
    obj=read(folder/'obj-phases.json')
    packets=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    rows=[]
    for f in summary['frames']:
        g=f['g'];es=[e for e in events if e['generation']==g]
        def allmarks(name):return [e for e in es if e['event']==name]
        bg,=allmarks('bg_map_frozen');source,=allmarks('source_begin')
        end,=allmarks('end_enter');prepare,=allmarks('prepare_enter')
        assert bg['sha256']==sha(folder/f'map-{g}.bin') and bg['clock']<=prepare['clock']<=end['clock']
        phase=obj[str(g)]
        draining=[e for e in allmarks('SPI') if end['clock']<=e['start']<phase['end_accepted']]
        maps=allmarks('map_packet_enter');enqueued=allmarks('map_enqueue')
        assert len(maps)==len(enqueued)
        info=dict(g=g,bg_frozen=bg['clock'],prepare=prepare['clock'],end_enter=end['clock'],
                  source_begin=source['clock'],first_span_last_writer=bg['first_span_last_writer'],
                  end_accepted=phase['end_accepted'],first_OBJ_ROM=phase.get('first_obj_rom_request'),
                  last_OBJ_ROM=phase.get('last_obj_rom_response'),map_packets=len(maps),
                  end_E8_polls=sum(e['opcode']=='0xe8' for e in draining),
                  end_bulk_E1=sum(e['opcode']=='0xe1' and e['packet_opcode']==7 for e in draining))
        if maps:
            first=maps[0];enqueue=enqueued[0]
            rowsent=next((b,t) for _,t,h,_ in packets if (b:=bytes.fromhex(h))[1]==2 and int.from_bytes(b[8:10],'little')==g)
            b,push=rowsent;length=int.from_bytes(b[12:14] if b[0]==2 else b[14:16],'little')
            assert first['offset']==enqueue['offset']==int.from_bytes(b[10:12],'little')==bg['first']*64
            assert length==bg['rows']*64 and len(maps)==len({e['offset'] for e in maps})
            assert bg['first_span_last_writer']<=first['clock']<=enqueue['clock']<=push<=f['first_map_ACK']
            assert not any(e.get('early') for e in maps[1:])
            expected=(folder/f'map-{g}.bin').read_bytes()[first['offset']:first['offset']+length]
            assert (b[16:] if b[0]==2 else b[16:]*(length//2))==expected
            credit=allmarks('map_credit_attempt')
            early=bool(first.get('early'))
            admission=('published' if early else 'no_attempt' if not credit else
                       'queue_reserve' if credit[0]['outstanding']>=3 else 'ready_bulk')
            info.update(first_offset=first['offset'],bytes=length,early=early,admission=admission,credit_attempt=credit,
                        packet_enter=first['clock'],enqueue=enqueue['clock'],push=push,first_ACK=f['first_map_ACK'],
                        from_source_ms=ms(push-source['clock']),BG_to_push_ms=ms(push-bg['clock']),
                        END_enter_to_accepted_ms=ms(phase['end_accepted']-end['clock']),
                        first_span_writer_to_BG_ms=ms(bg['clock']-bg['first_span_last_writer']) if bg['first_span_last_writer'] else None,
                        offer_to_enqueue_ms=ms(enqueue['clock']-first['clock']),enqueue_to_push_ms=ms(push-enqueue['clock']))
        else:assert bg['first'] is None
        rows.append(info)
    return rows


def analyze(a):
    previous=read(ROOT/'analysis/map526-verification.json')
    inputs=read(ROOT/'analysis/prefix523-verification.json')
    plans={f['generation']:f for f in read(ROOT/'analysis/obj518-verification.json')['plans']['frames']}
    calendar=Calendar(a.calendar);oracle=tiles(a.fixture,957);phases=[]
    for i,folders in enumerate(zip(a.baseline,a.obj,a.front)):
        variants={};milestones={};results={};base_keys=None
        for name,folder,arm in zip(('526','OBJ','frontier'),folders,a.arm):
            ref=dict(inputs['phases'][i]['candidate'],firmware=sha(arm/'obj-nes-100/firmware.stm'))
            s,keys=run_cost(folder,'row254',ref,plans,calendar,oracle)
            run=read(folder/'joint.json')
            s['workspace_end']=run['workspace_end']
            s['observed_stack_gap_B']=int(run['observed_stack_low'],16)-int(run['workspace_end'],16)
            variants[name]=s;milestones[name]=first_maps(folder,s)
            if name=='526':
                base_keys=keys
                old=previous['phases'][i]['variants']['row254']
                for key in ('window.csv','packets.jsonl','obj-phases.json'):assert s['pins'][key]==old['pins'][key],key
                assert s['final_ack']==old['final_ack'] and s['instructions']==old['instructions']
                continue
            base=variants['526']
            assert base['client']==s['client'] and base_keys==keys
            assert s['dma_B']==base['dma_B'] and s['ROM_reads']==base['ROM_reads']
            for g in range(905,958):assert sha(folder/f'frame-{g}.rgb')==sha(folders[0]/f'frame-{g}.rgb'),g
            result=dict(early_frames=sum(r.get('early',False) for r in milestones[name]),
                        admissions=dict(Counter(r.get('admission','empty_map') for r in milestones[name])),
                        dense_delta_ms=s['dense_ms']-base['dense_ms'],final_delta_ms=ms(s['final_ack']-base['final_ack']),
                        final_vs524_ms=ms(s['final_ack']-previous['phases'][i]['variants']['524']['final_ack']),targets={})
            for g in (952,954):
                b,c=[v['frames'][g-905] for v in (base,s)]
                m,o=[milestones[n][g-905] for n in (name,'526')]
                result['targets'][g]=dict(first_map_advance_ms=o['from_source_ms']-m['from_source_ms'],
                    early=m['early'],map_B=len(c['map_offsets'])*64,waits=c['final_waits'],
                    seal_waits=c['seal_waits'],gap_VBlanks=c['display_VBlanks'],gap_ms=c['gap_ms'],
                    first_OBJ_request_delta_ms=ms((m['first_OBJ_ROM']-m['source_begin'])-(o['first_OBJ_ROM']-o['source_begin'])),
                    last_OBJ_response_delta_ms=ms((m['last_OBJ_ROM']-m['source_begin'])-(o['last_OBJ_ROM']-o['source_begin'])))
            results[name]=result
        audit=read(a.replay[i]/'audit.json')
        assert audit['frames']==53 and audit['trace']==variants['frontier']['pins']['window.csv']
        for name,s in variants.items():
            s['display_clocks']=[f['ack'] for f in s['frames']]
            s['frames']=[f for f in s['frames'] if 951<=f['g']<=955]
            milestones[name]=[r for r in milestones[name] if 951<=r['g']<=955]
        phases.append(dict(start=previous['phases'][i]['start'],variants=variants,milestones=milestones,results=results,
                           independent_replay=audit))
    builds={}
    for n,arm in zip(('526','OBJ','frontier'),a.arm):
        blob=arm/'obj-nes-100/firmware.stm';sz=[int(x) for x in (arm.parent/'size.log').read_text().splitlines()[-1].split()[:3]]
        builds[n]=dict(sha256=sha(blob),bytes=blob.stat().st_size,Flash_free=0x34000-blob.stat().st_size,
                       text=sz[0],data=sz[1],BSS=sz[2])
    guards=[read(p) for p in a.guards]
    assert all(len(r['rows'])==9 and r['sha256']==builds[n]['sha256'] for n,r in zip(('OBJ','frontier'),guards))
    responses=read(a.responses)
    assert responses['passed'] and responses['cases']==40 and responses['candidate_SHA256']==builds['frontier']['sha256']
    assert sha(a.board/'output_files/board.sof')==previous['builds']['row254']['SOF']
    abort=[]
    for folder,kind,result in zip(a.abort,('guard','invalid_OBJ'),(2,5)):
        proof=read(folder/'guard-proof.json')
        assert proof==dict(injected=kind,last_display=905,aborted=906,runtime_result=result,invalidated_both_map_banks=True)
        packets=[bytes.fromhex(json.loads(line)[2]) for line in (folder/'packets.jsonl').read_text().splitlines()]
        assert [int.from_bytes(b[8:10],'little') for b in packets if b[0]==3]==[905]
        assert any(b[0] in (2,4) and b[1]==2 and int.from_bytes(b[8:10],'little')==906 for b in packets)
        assert not any(e['event']=='SPI' and e['opcode']=='0xea' and e['generation']==906 for e in read(folder/'events.json'))
        abort.append(dict(proof,no_seal_or_EA_906=True))
    return dict(phases=phases,builds=builds,guards=guards,response_cases=responses['cases'],abort=abort,
                unchanged_FPGA=previous['builds']['row254']['SOF'],physical_trial=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('baseline','obj','front','guards','abort','replay'):p.add_argument('--'+n,type=Path,nargs=2,required=True)
    p.add_argument('--arm',type=Path,nargs=3,required=True)
    for n in ('calendar','fixture','responses','board','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',encoding='utf8',newline='\n')
