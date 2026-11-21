"""Separate overlapped receiver work from SPI/credit time on the final section-5 pair."""
import argparse
import json
from pathlib import Path

from analyze_nes_section909 import coverage, measure, read_csv
from nes_section910 import BASE, WORK, FRAMED, DIRECT, sha
from test_nes_raw506_joint import MASTER


def ms(ticks):
    return round(ticks*1000/MASTER,6)


def bus_between(events,start,end):
    """Only charge the part of a transaction inside this interval."""
    totals={}
    for e in events:
        overlap=min(end,e['clock'])-max(start,e['start'])
        if overlap<=0:continue
        count,time=totals.get(e['opcode'],(0,0))
        totals[e['opcode']]=(count+1,time+overlap)
    return {op:[n,ms(t)] for op,(n,t) in totals.items()}


def trace(path,frame):
    window=[r for r in read_csv(path,'window.csv') if r['g']=='912']
    events=[e for e in json.loads((path/'events.json').read_bytes())
            if e.get('event')=='SPI' and e['generation']==912]
    pair=frame['section5_pair']
    assert [p['bytes'] for p in pair]==[201,240]
    oam=frame['last_accept']['OAM']
    table=pair[1]['accept']
    index,=[r['index'] for r in window if r['event']=='load' and int(r['clock'])==table]
    times={r['event']:int(r['clock']) for r in window if r['index']==index and r['op']=='2'}
    assert times['load']==table
    seal,=[e for e in events if e['opcode']=='0xe1' and e['packet_opcode']==3]
    assert seal['bytes']==187
    finish=frame['masterclocks']['SEAL']
    services=bus_between(events,table,seal['start'])
    result=dict(oam_to_201_ms=ms(pair[0]['issue']-oam),
                oam_to_201_SPI=bus_between(events,oam,pair[0]['issue']),
                table_to_SEAL_ms=ms(finish-table),before_SEAL_tx_ms=ms(seal['start']-table),
                before_SEAL_tx_SPI=services,SEAL_tx_ms=ms(seal['clock']-seal['start']),
                SEAL_queue_to_load_ms=ms(finish-seal['clock']),
                last_OBJ_relative_to_table_load_ms=ms(frame['masterclocks']['last_OBJ']-table),
                last_OBJ_return_relative_to_table_load_ms=ms(frame['last_OBJ_return']-table),
                table_load_to_retire_ms=ms(times['ack']-table),
                table_still_held_at_SEAL_queue_ms=ms(max(0,times['ack']-seal['clock'])),
                receiver_service_overlapping_SEAL_tx_ms=ms(max(0,min(times['ack'],seal['clock'])-max(table,seal['start']))))
    if 's910_data_check' in times:
        stages=['load','s910_data_check','s910_literal','s910_trigger','s910_after_trigger','s910_accepted','s910_reply','ack']
        assert [times[s] for s in stages]==sorted(times[s] for s in stages)
        result['receiver_from_table_load_ms']={s:ms(times[s]-table) for s in stages}
    return result


def guards(work):
    proof=work/'proof'
    fw=work/'link/src/obj-nes-100/firmware.stm'
    for name,key in [('loader.json','firmware'),('timer.json','firmware'),('menu.json','firmware'),('base/result.json','firmware_sha256')]:
        assert json.loads((proof/name).read_bytes())[key]==sha(fw)
    cases=json.loads((proof/'sram.json').read_bytes())['cases']
    assert len(cases['normal']['d0_sites'])==4 and cases['normal']['checked_retire'] and not cases['bad-crc']['checked_retire']
    assert json.loads((proof/'timer.json').read_bytes())['passed']
    assert json.loads((proof/'menu.json').read_bytes())['rows']['normal']['released']
    assert json.loads((proof/'base/result.json').read_bytes())['safe_return']
    return dict(flash=fw.stat().st_size,firmware=sha(fw),SRAM_proof=sha(proof/'sram.json'))


def compare(temp):
    results={}
    for phase in (1,2):
        for state in ('warm','cold'):
            condition=results[f'p{phase}-{state}']={}
            def directory(tag):
                return temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{state}-pair'
            original,original_body=measure(directory('907'),BASE)
            for tag,work in [('910ref',BASE),('910',WORK),('910b',FRAMED),('910c',DIRECT)]:
                path=directory(tag)
                run,body=measure(path,work)
                assert run['parameters']==original['parameters'] and run['client']==original['client']
                if tag=='910ref':
                    assert run==original and body==original_body  # Added Lua markers cost zero emulated clocks.
                for g in range(905,913):
                    for tile in (False,True):
                        assert ([b for b in body[g] if (b[0]==7)==tile] ==
                                [b for b in original_body[g] if (b[0]==7)==tile])
                    assert sha(path/f'frame-{g}.rgb')==sha(directory('907')/f'frame-{g}.rgb')
                rows={}
                for g,frame in run['frames'].items():
                    old=original['frames'][g]
                    assert frame['section5_hash']==old['section5_hash']
                    prior=coverage(original['preDMA'][g]);new=coverage(run['preDMA'][g])
                    rows[g]=dict(display=frame['VBlank'][3],baseline_display=old['VBlank'][3],
                                 advanced_DMA_B=len(new),baseline_advanced_DMA_B=len(prior),
                                 lost_B=len(prior.keys()-new.keys()),
                                 late_B=sum(prior[k]<new[k] for k in prior.keys()&new.keys()))
                end=run['frames'][912]
                previous=original['frames'][912]
                condition[tag]=dict(intervals=run['intervals'],ACK=run['final_ACK'],
                                    ACK_delta_ms=ms(run['final_ACK']-original['final_ACK']),
                                    OAM_delta_ms=ms(end['last_accept']['OAM']-previous['last_accept']['OAM']),
                                    first201_issue_delta_ms=ms(end['section5_pair'][0]['issue']-previous['section5_pair'][0]['issue']),
                                    SEAL_delta_ms=ms(end['masterclocks']['SEAL']-previous['masterclocks']['SEAL']),
                                    ARM_E0_delta_ms=ms(run['frames'][912]['masterclocks']['E0_response']-
                                                       original['frames'][912]['masterclocks']['E0_response']),
                                    focal=trace(path,run['frames'][912]),frames=rows)
    proofs={}
    reference=json.loads((WORK/'proof/rows910-reference.json').read_bytes())
    assert reference['firmware']==sha(BASE/'link/src/obj-nes-100/firmware.stm') and len(reference['spans'])==9
    for tag,work in [('910',WORK),('910b',FRAMED),('910c',DIRECT)]:
        proof=proofs[tag]=guards(work)
        directed=json.loads((work/'proof/rows910.json').read_bytes())
        assert directed['firmware']==proof['firmware'] and directed['spans']==reference['spans']
        proof['section5_directed_cases']=len(directed['spans'])
    return dict(guards=proofs,conditions=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(compare(args.temp),indent=2)+'\n',encoding='utf8')
