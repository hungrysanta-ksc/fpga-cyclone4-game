"""Join passive ARM timestamps, bounded cache controls and the observed RTL deadlines."""
import argparse
import json
from pathlib import Path

from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage
from analyze_nes_tail961 import hardware, milliseconds
from check_nes_blank959 import directory, read, rows, summary
from nes_blank960 import WORK
from test_nes_service509_schedule import Calendar


def analyze(temp):
    result={}
    calendar=Calendar(temp/'nes-service509-rom03')
    for p in (1,2):
        baseline=directory(temp,p,'961wirepair','cold')
        marks=read(directory(temp,p,'962source','cold')/'origin962.json')
        original=read(Path('analysis/tail961-results.json'))['phases'][str(p)]['cold_961wirepair']
        budget=original['first_E9_909']
        last=budget['previous_calendar_grant']
        assert last in [x+(last//calendar.period)*calendar.period for x in calendar.starts]
        events=read(baseline/'events.json')
        inputs=[e for e in events if e.get('input_generation')==909 and e.get('opcode') in ('0xd1','0xd2')]
        assert len(inputs)==38
        def block(at):
            assert sum(e['clock']<=at and e['opcode']=='0xd1' for e in inputs)==1+sum(
                e['clock']<=at and e['opcode']=='0xd2' for e in inputs)
            return sum(e['clock']<=at and e['opcode']=='0xd1' for e in inputs)
        f,=marks['fragments']
        assert f['masks']=={'0':255} and f['rank']==0 and f['index']==8
        assert bytes.fromhex(marks['emit'][0][1])==bytes.fromhex('818d033900020cff')
        e9=next(e for e in events if e.get('opcode')=='0xe9' and e['generation']==909)
        stages=dict(raw_object=f['object_write'],raster=f['raster_write'],tile_kind=marks['tile_write'],
                    last_D2=round(inputs[-1]['clock']),planner=marks['planner'],mask_checked=marks['resolve'][0][0],
                    slot_record=marks['emit'][0][0],E9_start=round(e9['start']),E9_seal=round(e9['clock']))
        assert sorted(stages.values())==list(stages.values())
        phase=dict(ARM=marks,input_blocks=[block(stages[k]) for k in ('raw_object','raster','tile_kind')],
                   last_grant=last,stage_clocks=stages,relative_ms={k:milliseconds(v-last) for k,v in stages.items()},
                   E9_bytes=e9['bytes'],cases={})
        slots=[(last//calendar.period)*calendar.period+g for g in calendar.starts
               if stages['planner']<=(last//calendar.period)*calendar.period+g<=last]
        assert len(slots)>=64
        phase['grant_count_after_planner']=len(slots)
        phase['latest_first_of_64']=slots[-64]
        phase['planner_to_latest_first_ms']=milliseconds(slots[-64]-stages['planner'])
        at=slots[-64]
        for expected in slots[-64:]:
            grant,reply=calendar.select(at)
            assert grant==expected
            at=reply+3
        assert marks['complete_groups']==[dict(base=3072,through_object=45)]
        checks0=measure(baseline,WORK)[1]
        for name in ('961wirepair','962one','962four','962page'):
            tag='962onewire' if (name,p)==('962one',1) else name
            folder=directory(temp,p,tag,'cold')
            s=summary(folder,baseline)
            metrics,checks=measure(folder,WORK)
            assert checks==checks0
            h,_,_=hardware(folder,909)
            assert h['samples'][1]==0
            fr=metrics['frames'][912]
            record=dict(replay=tag,reveals=s['reveals'],six=s['six'],ACK912=s['ACK912'],D2_before_911=s['D2_before_911_reveal'],
                        seal909=metrics['frames'][909]['clocks']['SEAL'],show909=metrics['frames'][909]['clocks']['show'],
                        preDMA912=fr['preDMA'],
                        DMA_before_SEAL912=len(coverage([r for r in fr['preDMA'] if r[3]==fr['VBlank'][3]-1])),
                        RTL_909_E8=h['samples'],longest_foreground=h['longest'],foreground_reads=h['foreground_reads'])
            if name!='961wirepair':
                r=read(folder/'gen909/budget962.json')
                record['assumed_row_fills']=len(r['slots'])
                record['last_assumed_reply']=r['slots'][-1][-1]
                record['ACK_delta_ms']=milliseconds(record['ACK912']-original['ACK912'])
            if name in ('961wirepair','962page'):
                loads=[r for r in rows(folder/'window.csv') if r['g']=='912' and r['op']=='7' and r['event']=='load']
                jobs=[r for r in map(json.loads,(folder/'producer.jsonl').read_text().splitlines()) if r['generation']==912]
                data={}
                for job,load in zip(jobs,loads,strict=True):
                    if job['token'] in (35,36):
                        data[job['token']]=dict(bytes=job['bytes'],ready=round(job['producer']),
                                                load=int(load['clock']),line=int(load['line']))
                assert [r['bytes'] for r in data.values()]==[288,32]
                record['tail912']=data
            phase['cases'][name]=record
        result[p]=phase
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    print(json.dumps(analyze(p.parse_args().temp),indent=2))
