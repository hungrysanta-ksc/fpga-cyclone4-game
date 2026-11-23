"""Match DMA work and identify the last physical ROM grant before an OBJ stall."""
import argparse
import bisect
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_chain935 as chain
from analyze_nes_wait936 import analyze

from analyze_nes_credit946 import directory, job_times, ordinary_packets, read, sha
from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage, read_csv
from nes_deadline947 import BASE, MODES, ROM, work
from test_nes_raw506_joint import PERIOD, MASTER
from test_nes_service509_schedule import Calendar


def ready_bytes(folder):
    jobs=job_times(folder)
    out={}
    for line in (folder/'packets.jsonl').read_text().splitlines():
        packet=bytes.fromhex(json.loads(line)[2])
        if packet[0]!=7:
            continue
        generation=int.from_bytes(packet[8:10],'little')
        offset=int.from_bytes(packet[10:12],'little')
        count=int.from_bytes(packet[14:16],'little')
        token=int.from_bytes(packet[16:20],'little')
        ready=jobs[generation,token,packet[1],count]
        for pos in range(offset,offset+count):
            key=(generation,packet[1],pos)
            assert key not in out
            out[key]=(token,ready)
    return out


def inspect(folder, arm, calendar):
    fw=arm/'link/src/obj-nes-100/firmware.stm'
    joint=read(folder/'joint.json')
    assert joint['passed'] and joint['firmware_SHA256']==sha(fw) and joint['client_SHA256']==sha(ROM/'sink165.sfc')
    timing, quality=measure(folder,arm)
    window=read_csv(folder,'window.csv')
    last=timing['frames'][912]
    capture=timing['frames'][910]['commit_D2']
    supply=read(folder/'grants904.json')
    events=read(folder/'events.json')
    batches=read(folder/'e9931.json')
    stages={}
    shows={int(r['g']):int(r['clock']) for r in window if r['event']=='reveal'}
    for g in (908,909,910,911,912):
        frame=timing['frames'][g]
        waits=[row for row in supply if row[:2]==[g,1]]
        maxwait=None
        if waits:
            _,_,req,grant,reply=max(waits,key=lambda r:r[3]-r[2])
            assert grant%calendar.period in calendar.starts
            index=bisect.bisect_left(calendar.starts,req%calendar.period)-1
            previous=(req//calendar.period-(index<0))*calendar.period+calendar.starts[index]
            maxwait=dict(request=req,grant=grant,reply=reply,wait=grant-req,previous=previous,
                         advance_at_least=req-previous)
        def event(name):
            return next(int(r['clock']) for r in window if r['g']==str(g) and r['event']==name)
        plan=[e for e in events if e.get('opcode')=='0xe9' and e['generation']==g]
        schedule=[r['records'] for r in batches if r['g']==g]
        assert len(schedule)==len(plan)
        pops=[e for e in events if e.get('opcode')=='0xd2' and e.get('input_generation')==g]
        assert round(pops[-1]['clock'])==frame['commit_D2']
        polls=[bytes.fromhex(e['reply']) for e in events if e.get('opcode')=='0xe8' and e.get('generation')==g]
        stages[g]=dict(empty_E8=sum(r[3]==0 and r[6]==0 for r in polls),E8=len(polls),
            data_blocks_before_show=sum(e['clock']<shows[g-1] for e in pops[:-1]),
            data_blocks=len(pops)-1, ARM_E0=frame['clocks']['E0_response'],ACK=frame['clocks']['ACK'],capture=frame['capture_ready'],input_first=frame['first_D1'],commit_D2=frame['commit_D2'],
            first_E9=round(plan[0]['start']),last_E9=round(plan[-1]['clock']), batches=list(map(len,schedule)),
            last_OBJ=frame['clocks']['last_OBJ'],last_return=frame['last_OBJ_return'],SEAL=frame['clocks']['SEAL'],
            upload=event('upload165_entry'),DMA=frame['clocks']['DMA_start'],show=frame['clocks']['show'],
            frame=frame['VBlank'][3],line=frame['line'][3],residual_B=sum(frame['residual_DMA']),
            max_ROM_wait=maxwait)
    pre=last['preDMA']
    writes=[r for r in window if r['g']=='912' and int(r['clock'])<last['clocks']['SEAL']
            and r['event'] in ('ppu_dma','ppu_last')]
    previous=last['VBlank'][3]-1
    starts={}
    ends={}
    for (_,address,size,frame),start,end in zip(pre,writes[::2],writes[1::2],strict=True):
        assert start['event']=='ppu_dma' and end['event']=='ppu_last'
        assert int(start['value'])==size and int(start['frame'])==int(end['frame'])==frame
        if frame==previous:
            starts[address,size]=int(start['clock'])
            ends[address,size]=int(end['clock'])
    before=ends.get((0x8ca0,288))
    after=starts.get((0x8440,32))
    tail=False
    for line in (folder/'beam934.csv').read_text().splitlines():
        event,*fields=line.split(',')
        tick,frame,_,addr,count,beam,_=map(int,fields)
        if (before and after and before<tick<=after and frame==previous and addr==0x8440 and count==32
                and 225<=beam<=252 and event in ('grant','grant935')):
            tail=True
    return dict(prior_blank_B=len(coverage([r for r in pre if r[3]==previous])),tail_grant=tail,
        sha256=sha(fw),Flash=fw.stat().st_size,gaps=timing['gaps'],total=timing['intervals'],
        final_ACK=timing['final_ACK'],capture_D2=capture,preDMA=last['preDMA'],stages=stages),quality


def report(temp,modes,*,prefix='947',work=work):
    cal=Calendar(temp/'nes-service509-rom03')
    result=dict(master_Hz=MASTER,physical=False,ROM=sha(ROM/'sink165.sfc'),cases={})
    for cache in ('warm','cold'):
        for phase in (1,2):
            case=cache+str(phase)
            group=result['cases'][case]={}
            ref=directory(temp,phase,'946objguard',cache)
            reference,expected=inspect(ref,BASE,cal)
            target=directory(temp,phase,'935boundedfinal',cache)
            with patch.object(chain,'output',lambda _:ROM):
                baseline=analyze(temp,'objguard',phase,cache,tag='946objguard',arm=BASE)
            deadline=reference['capture_D2']+baseline['capture_margin']
            supply935=ready_bytes(target)
            group['946']=reference
            capture911=reference['stages'][911]['capture']-240*341*4
            if cache=='cold':
                capture911-=PERIOD
            reference['D2_minus_target911']=reference['capture_D2']-capture911
            for mode in modes:
                folder=directory(temp,phase,prefix+mode,cache)
                row,actual=inspect(folder,work(mode),cal)
                assert all(actual[k]==expected[k] for k in ('map','colors','RGB','sections','tiles'))
                assert ordinary_packets(folder)==ordinary_packets(ref)
                row['D2_minus_target911']=row['capture_D2']-capture911
                row['advance_ACK']=reference['final_ACK']-row['final_ACK']
                row['capture_margin']=deadline-row['capture_D2']
                row['exact_preDMA']=coverage(row['preDMA']).keys()==coverage(reference['preDMA']).keys()
                times,prior=job_times(folder),job_times(target)
                row['same_jobs']=times.keys()==prior.keys()
                row['late_vs935']=[(k,v-prior[k]) for k,v in times.items() if k in prior
                                    and k[:2] not in ((912,32),(912,35)) and v>prior[k]]
                supplied=ready_bytes(folder)
                assert supplied.keys()==supply935.keys()
                deltas=[supplied[key][1]-ready for key,(token,ready) in supply935.items()
                        if (key[0],token) not in ((912,32),(912,35))]
                row['supply_vs935']=dict(compared_bytes=len(deltas),later_bytes=sum(d>0 for d in deltas),
                                         max_late_clocks=max(0,max(deltas)))
                late={}
                for key,(token,ready) in supply935.items():
                    delay=supplied[key][1]-ready
                    if delay>0 and (key[0],token) not in ((912,32),(912,35)):
                        count,peak=late.get((key[0],token), (0,0))
                        late[key[0],token]=(count+1,max(peak,delay))
                row['late_destinations']=[dict(generation=g,reference_token=t,bytes=n,clocks=d)
                                          for (g,t),(n,d) in sorted(late.items())]
                group[mode]=row
                print(case,mode,row['Flash'],row['total'],row['advance_ACK'],row['capture_margin'],
                      row['exact_preDMA'],row['same_jobs'],len(row['late_vs935']),flush=True)
    result['gates']={}
    for mode in modes:
        rows=[g[mode] for g in result['cases'].values()]
        result['gates'][mode]=dict(Flash=rows[0]['Flash']<=212992,
            faster_all=all(r['advance_ACK']>0 and r['total']<g['946']['total']
                for g,r in zip(result['cases'].values(),rows)),
            capture=all(r['capture_margin']>=0 for r in rows),
            other_tiles=all(r['supply_vs935']['later_bytes']==0 for r in rows),
            no_later_ACK=all(r['advance_ACK']>=0 for r in rows),
            cold_preDMA=all(r['exact_preDMA'] and r['prior_blank_B']==496 and r['tail_grant'] for r in rows[2:]))
        gate=result['gates'][mode]
        gate['warm13_cold14']=all(r['total']<=limit for r,limit in zip(rows,(13,13,14,14)))
        gate['input17']=all(r['stages'][909]['data_blocks_before_show']>=17 for r in rows[2:])
        gate['eligible']=all(gate[k] for k in
            ('Flash','capture','other_tiles','cold_preDMA','no_later_ACK','warm13_cold14','input17'))
    result['selected']='946' if not any(g['eligible'] for g in result['gates'].values()) else None
    result['recovery']={}
    for mode in modes:
        path=work(mode)/f'safety{prefix}.json'
        if path.exists():
            safety=read(path)
            assert safety['consumer']==result['ROM'] and safety['firmware']==result['cases']['warm1'][mode]['sha256']
            result['recovery'][mode]=safety
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('modes',choices=MODES,nargs='+')
    args=parser.parse_args()
    args.out.write_text(json.dumps(report(args.temp,args.modes),indent=2)+'\n',encoding='utf-8')
