"""Compare physical OBJ DMA, checked END and the next input on one master clock."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import analyze_nes_chain935 as chain
import analyze_nes_obj923 as obj
from analyze_nes_palette921 import directory, read, read_csv, sha
from analyze_nes_return930 import jobs
from analyze_nes_rows931 import job_times
from analyze_nes_wait936 import analyze
from nes_oam937 import base, output, work


def ordinary_packets(folder):
    by_section=defaultdict(list)
    for _,_,wire,_ in map(json.loads,(folder/'packets.jsonl').read_text().splitlines()):
        data=bytes.fromhex(wire)
        if data[0] in (2,4,8):
            # Per-frame section order, offset, extent and payload. Exclude
            # the two-byte packet sequence, which may change with cross-section arbitration.
            by_section[(int.from_bytes(data[8:10],'little'),data[1])].append(data[:2]+data[4:])
    return by_section


def phase_case(temp,mode,phase,cache):
    baseline=mode=='batchfast'
    tag=('936' if baseline else '937')+mode
    arm=base(mode) if baseline else work(mode)
    result=analyze(temp,mode,phase,cache,tag=tag,arm=arm)
    folder=directory(temp,phase,tag,cache)
    events=read(folder/'events.json')
    win=read_csv(folder,'window.csv')
    terminal=next(e for e in events if e.get('generation')==909 and e.get('opcode')=='0xe8'
                  and bytes.fromhex(e['reply'])[3]==2)
    begin=next(e for e in events if e.get('event')=='source_begin' and e['generation']==910)
    assert begin['previous_output']==909
    returned=max(int(r['clock']) for r in win if r['g']=='909' and r['event']=='ack' and
                 r['op']=='7' and r['section']=='1')
    result.update(END_snapshot=round(terminal['clock']),final_OBJ_return=returned,
                  source_offer=round(begin['clock']),data_ready_before_show=result['clocks909']['show']-result['data_D2'])
    ref=directory(temp,phase,'936batchfast',cache)
    packets=ordinary_packets(folder)
    assert packets==ordinary_packets(ref)
    result['matching_ordinary_packets']=sum(map(len,packets.values()))
    current,original=job_times(folder),job_times(ref)
    assert current.keys()==original.keys()
    later=[(v-original[k],list(k)) for k,v in current.items()
           if k[:2] not in ((912,32),(912,35)) and v>original[k]]
    result.update(later_vs936=len(later),max_delay_vs936=max(later,default=(0,None)))
    if cache=='warm':
        clocks={k:v['clocks'] for k,v in jobs(folder,(22,23,24),generation=909).items()}
        result['last_OBJ909']=clocks
        reference=directory(temp,phase,'935boundedfinal',cache)
        ref_clocks=jobs(reference,(22,),generation=909)[22]['clocks']
        result['token22_delta_vs935']={key:value-ref_clocks[key] for key,value in clocks[22].items()}
        result['acks_while_token22_queued']=[(r['op'],r['section'],int(r['clock']))
                for r in win if r['g']=='909' and r['event']=='ack' and
                clocks[22]['E1']<=int(r['clock'])<=clocks[22]['load']]
        start,end=clocks[23]['ready'],clocks[24]['ready']
        grants=read(folder/'grants904.json')
        result['OBJ_23_to_24']=dict(interval=end-start,
                demand_grants=sum(g==909 and kind==1 and req<end and reply>start
                                  for g,kind,req,grant,reply in grants),
                after_22_return=end-clocks[22]['returned'],
                release_22_to_E8_24=clocks[24]['E8']-clocks[22]['returned'])
    return result


def report(temp,modes):
    result=dict(clock_Hz=21477272,physical=False,ROM_sha256=sha(output('bounded')/'sink165.sfc'),runs={})
    for mode in ('batchfast',*modes):
        base_mode=mode=='batchfast'
        arm=base(mode) if base_mode else work(mode)
        tag=('936' if base_mode else '937')+mode
        binary=arm/'link/src/obj-nes-100/firmware.stm'
        cases={}
        entry=dict(Flash=binary.stat().st_size,sha256=sha(binary),cases=cases)
        checked=arm/'span-check/result.json'
        if checked.exists():
            entry['span_check']=read(checked)
            assert entry['span_check']['firmware_sha256']==entry['sha256']
        result['runs'][mode]=entry
        for cache in ('warm','cold'):
            for phase in (1,2):
                folder=directory(temp,phase,tag,cache)
                if (folder/'joint.json').exists():
                    cases[cache+str(phase)]=phase_case(temp,mode,phase,cache)
        if len(cases)==4:
            ref=result['runs']['batchfast']['cases']
            ref935=read(Path(__file__).resolve().parents[1]/'analysis/wait936-results.json')['runs']['935']['cases']
            entry['gates']=dict(warm13=all(cases[k]['total']==13 for k in ('warm1','warm2')),
                                capture=all(cases[k]['capture_margin']>=0 for k in ('warm1','warm2')),
                                cold496_15=all(cases[k]['early912']==496 and cases[k]['tail'] and cases[k]['total']==15 for k in ('cold1','cold2')),
                                ACK_no_later_than_936=all(row['ACK912']<=ref[k]['ACK912'] for k,row in cases.items()),
                                ACK_no_later_than_935=all(row['ACK912']<=ref935[k]['ACK912'] for k,row in cases.items()),
                                ACK_earlier_than_925=all(row['ACK912']<row['ACK925'] for row in cases.values()),
                                other_tiles_no_later_than_935=all(row['later_vs935']==0 for row in cases.values()),
                                Flash_fit=entry['Flash']<=212992)
        if not base_mode and (arm/'final-stops.json').exists():
            with patch.object(obj,'client',lambda _:output('bounded')),patch.object(chain,'fit_arm',lambda:arm):
                entry['guards']=obj.recovery('final',arm,trial=arm)
                entry['markers']=chain.markers()
            entry['edges']={f'{p}-{event}':read(path) for p in (1,2) for event in ('stop','head')
                            if (path:=directory(temp,p,tag,'cold')/f'edge935-{event}-verified.json').exists()}
        if not base_mode and 'gates' in entry:
            entry['gates']['both_cold_priority_edges']=len(entry.get('edges',{}))==4
            entry['gates']['linked_recovery_checked']='guards' in entry and 'markers' in entry
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('out',type=Path);p.add_argument('modes',nargs='+')
    args=p.parse_args()
    args.out.write_text(json.dumps(report(args.temp,args.modes),indent=2)+'\n',encoding='utf-8')
