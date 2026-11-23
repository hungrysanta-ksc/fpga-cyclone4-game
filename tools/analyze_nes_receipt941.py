"""Decompose 906's last plan and compare identical tiles and display deadlines."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_chain935 as chain
from analyze_nes_input940 import timeline
from analyze_nes_oam937 import ordinary_packets
from analyze_nes_palette921 import directory, read, read_csv, sha
from analyze_nes_rows931 import job_times
from analyze_nes_return930 import jobs
from analyze_nes_wait936 import analyze
from nes_receipt941 import ARM, image


def stages(folder):
    bank=read(folder/'banks904.json')['906']['banks557'][-1]
    assert (bank['first'],bank['count'],bank['decoded'])==(77,10,10)
    first,release=bank['first_check'],bank['release']
    tiles=job_times(folder)
    blocked=read(folder/'rows911.json')['blocked']['6']
    ret=dict(read(folder/'returns904.json'))[6]
    ready=tiles[906,6,1,576]
    e8=next(round(e['clock']) for e in read(folder/'events.json') if e.get('generation')==906 and
            e.get('opcode')=='0xe8' and bytes.fromhex(e['reply'])[14:18]==(6).to_bytes(4,'little'))
    events=[e for e in read(folder/'events.json') if e.get('opcode')=='0xe1']
    heads=iter(r for r in read_csv(folder,'window.csv') if r['event']=='load')
    for line,e in zip((folder/'packets.jsonl').read_text().splitlines(),events,strict=True):
        packet=bytes.fromhex(json.loads(line)[2])
        head=next(heads)
        assert (int(head['op']),int(head['section']),int(head['g']))==(packet[0],packet[1],int.from_bytes(packet[8:10],'little'))
        if packet[:2]==bytes((7,1)) and int(head['g'])==906 and int.from_bytes(packet[16:20],'little')==6:
            assert int.from_bytes(packet[14:16],'little')==576
            e1,load=round(e['clock']),int(head['clock'])
            break
    assert blocked[0]==906 and ready<blocked[1]<ret<=release and ready<=e8<=e1<=load<ret
    demand=[(kind,req,grant,reply) for g,kind,req,grant,reply in read(folder/'grants904.json')
            if g==906 and first<=req<=release]
    assert demand and demand[-1][-1]<=blocked[1]
    spec=[r for r in read(folder/'ahead911.json') if r[0]==906 and first<=r[2]<=release]
    page=[r for r in read(folder/'pages933.json')['grants'] if r[0]==906 and first<=r[2]<=release]
    end=tiles[906,8,1,64]
    assert end==release+1
    return dict(first=first,plan_accepted=round(bank['seal']),release=release,token8=end,ready576=ready,
                E8=e8,E1=e1,load576=load,returned576=ret,both_banks_full=blocked[1],
                first_to_blocked=blocked[1]-first,bank_wait=ret-blocked[1],after_return=end-ret,
                demand_count=len(demand),demand_wait=sum(grant-req for _,req,grant,reply in demand),
                demand_service=sum(reply-grant for _,req,grant,reply in demand),last_reply=demand[-1][-1],
                speculative_grants=len(spec),page_grants=len(page),demand=demand)


def report(temp,modes):
    data=dict(master_Hz=21477272,actual_hardware=False,ARM=sha(ARM/'link/src/obj-nes-100/firmware.stm'),cases={},links={})
    for mode in modes:
        rom=image(mode)
        build=read(rom/'build.json')
        link=data['links'][mode]=dict(sha256=sha(rom/'sink165.sfc'),body=sha(rom/'body.bin'),
            ROM_free=build['physical_free_B'],loader_B=build['loader_B'],encoded_B=build['encoded_B'])
        for key,name in [('recovery','recovery941.json'),('faults','faults941.json')]:
            if (rom/name).exists():link[key]=read(rom/name)
        boot=temp/f'nes-receipt941-boot-{mode}'/'result.json'
        if boot.exists():
            link['boot']=read(boot)
            assert link['boot']['cases'][-1]['ROM']==link['sha256'] and link['boot']['passed']
        link['priority']={}
        for phase in (1,2):
            for edge in ('head','stop'):
                obs=directory(temp,phase,'941'+mode,'cold')/f'edge935-{edge}-verified.json'
                if obs.exists():link['priority'][f'{phase}-{edge}']=read(obs)
    for cache in ('warm','cold'):
        for phase in (1,2):
            key=cache+str(phase)
            rows=data['cases'][key]={}
            ref,old,prior=[directory(temp,phase,k,cache) for k in ('935boundedfinal','940handoffdecode','938fit')]
            prev,old_jobs,prior_jobs=map(job_times,(ref,old,prior))
            for m,d in [('935',ref),('940',old)]+[(m,directory(temp,phase,'941'+m,cache)) for m in modes]:
                row=rows[m]=dict(stages=stages(d),startup=(d/'startup-clock.txt').read_text().strip())
                if key=="cold1" and m in ("935","940","prefix"):
                    row["next_OBJ"]= {token:job["clocks"] for token,job in jobs(d,(19,20,22,24),generation=909).items()}
                for g in (909,911):
                    row[str(g)]=timeline(d,g)
                if m in ('935','940'):continue
                assert ordinary_packets(d)==ordinary_packets(old)
                with patch.object(chain,'output',lambda _:image(m)):
                    stats=analyze(temp,m,phase,cache,tag='941'+m,arm=ARM)
                times=job_times(d)
                late=[(k,t-prev[k]) for k,t in times.items() if t>prev[k] and k[:2] not in ((912,32),(912,35))]
                assert len(late)==stats['later_vs935']
                objs=((909,22,1,64),(909,24,1,352))
                row.update(late_vs935=late,gaps=stats['gaps'],total=stats['total'],ACK=stats['ACK912'],
                           early912=stats['early912'],tail=stats['tail'],capture=stats['capture_margin'],
                           OBJ_vs940=[times[k]-old_jobs[k] for k in objs],
                           OBJ_vs938=[times[k]-prior_jobs[k] for k in objs])
                row['ACK_vs935']=row['ACK']-read(ref/'joint.json')['frames'][-1]['ACK_masterclock']
    for mode in modes:
        cases=[group[mode] for group in data['cases'].values()]
        warm,cold=cases[0]['909'],cases[3]['911']
        ref_w=timeline(directory(temp,1,'939tile','warm'),909)
        ref_c=timeline(directory(temp,2,'939tile','cold'),911)
        link=data['links'][mode]
        link['gates']=dict(
            earlier_906=all(group[mode]['stages']['token8']<group['935']['stages']['token8'] for group in data['cases'].values()),
            input_940_gains=all(warm[k]<ref_w[k] for k in ('begin_minus_show','first_D1','planner')) and
                           all(cold[k]<ref_c[k] for k in ('begin_to_planner','planner')),
            input_no_later_940=all(warm[k]<=data['cases']['warm1']['940']['909'][k] for k in ('begin_minus_show','first_D1','planner')) and
                               all(cold[k]<=data['cases']['cold2']['940']['911'][k] for k in ('begin_to_planner','planner')),
            OBJ_earlier_than_938=all(max(r['OBJ_vs938'])<0 for r in cases),
            OBJ_no_later_940=all(max(r['OBJ_vs940'])<=0 for r in cases),
            warm13=all(r['total']==13 for r in cases[:2]),
            cold15_496=all(r['total']==15 and r['early912']==496 and r['tail'] for r in cases[2:]),
            capture=all(r['capture']>=0 for r in cases),
            all_tiles_no_later_935=all(not r['late_vs935'] for r in cases),
            ACK_no_later_935=all(r['ACK_vs935']<=0 for r in cases),
            guards='recovery' in link and 'faults' in link and len(link['priority'])==4 and 'boot' in link)
    return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.modes),indent=2)+'\n',encoding='utf8')
