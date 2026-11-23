"""Attribute the token 20 supply path and test continuous-frame gates."""
import argparse
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import analyze_nes_obj923 as obj
from analyze_nes_oam937 import ordinary_packets
from analyze_nes_palette921 import directory, read, sha
from analyze_nes_return930 import jobs
from analyze_nes_rows931 import job_times
from analyze_nes_wait936 import analyze
from nes_chain935 import output
from nes_head939 import MODES, work


def first_bg(folder,generation):
    events=[e for e in read(folder/'events.json') if e.get('generation')==generation]
    begin=next(e for e in events if e['event']=='source_begin')
    planner=next(e for e in events if e['event']=='planner_enter')
    plan=next(e for e in events if e.get('opcode')=='0xe9')
    token,ready=min(((k[1],v) for k,v in job_times(folder).items()
                     if k[0]==generation and k[2]==0),key=lambda pair:pair[1])
    return dict(token=token,source_begin=round(begin['clock']),planner=round(planner['clock']),
                first_E9=round(plan['clock']),ready=ready)


def stage(folder):
    tiles=jobs(folder,(19,20,22,24),generation=909)
    marks=tiles[20]['clocks']
    visible=[e for e in read(folder/'events.json') if marks['ready']<=e.get('clock',0)<=marks['E8']+0.5 and 'opcode' in e]
    phases=('ready','E8','E1','load','returned')
    return dict(first_BG={g:first_bg(folder,g) for g in (909,911)},
                token20=marks,stage_clocks={b:marks[b]-marks[a] for a,b in zip(phases,phases[1:])},
                SPI_before_discovery=dict(Counter(e['opcode'] for e in visible)),
                token19_return=tiles[19]['clocks']['returned'],token19_ack=tiles[19]['clocks']['head_ACK'],
                token22=tiles[22]['clocks'],token24_ready=tiles[24]['clocks']['ready'])


def report(temp,modes):
    data=dict(master_Hz=21477272,physical=False,ROM=sha(output('bounded')/'sink165.sfc'),cases={},links={})
    for mode in modes:
        arm=work(mode)
        f=arm/'link/src/obj-nes-100/firmware.stm'
        link=dict(Flash=f.stat().st_size,SHA256=sha(f))
        if (arm/'dispatch938.json').exists():
            link['dispatch']=read(arm/'dispatch938.json')
            assert link['dispatch']['firmware']==link['SHA256']
        if (arm/'final-stops.json').exists():
            with patch.object(obj,'client',lambda _:output('bounded')):
                link['guards']=obj.recovery('final',arm,trial=arm)
            link['priority_edges']={}
            for phase in (1,2):
                for edge in ('head','stop'):
                    path=directory(temp,phase,'939'+mode,'cold')/f'edge935-{edge}-verified.json'
                    if path.exists():
                        link['priority_edges'][f'{phase}-{edge}']=read(path)
        data['links'][mode]=link
    for cache in ('warm','cold'):
        for phase in (1,2):
            key=f'{cache}{phase}'
            cases=data['cases'][key]={}
            ref,base=[directory(temp,phase,tag,cache) for tag in ('935boundedfinal','938fit')]
            times=job_times(ref)
            control=read(Path(__file__).resolve().parents[1]/'analysis/wait936-results.json')['runs']['935']['cases'][key]
            cases['935']=stage(ref)
            cases['938']=stage(base)
            original=ordinary_packets(base)
            for mode in modes:
                arm=work(mode)
                folder=directory(temp,phase,'939'+mode,cache)
                stat=analyze(temp,mode,phase,cache,tag='939'+mode,arm=arm)
                assert ordinary_packets(folder)==original
                by_job=job_times(folder)
                assert by_job.keys()==times.keys()
                late=[dict(job=k,delay=v-times[k]) for k,v in by_job.items()
                      if v>times[k] and k[:2] not in ((912,32),(912,35))]
                assert len(late)==stat['later_vs935']
                row=stage(folder)
                row.update(intervals=stat['gaps'],total=stat['total'],preSEAL=stat['early912'],
                           tail_DMA=stat['tail'],capture_margin=stat['capture_margin'],
                           ACK912=stat['ACK912'],ACK_delta935=stat['ACK912']-control['ACK912'],
                           late_vs935=late,other_count=stat['other_count'],
                           before_OAM=row['token22']['load']<stat['OAM909'])
                # Token 8 reuses the bank returned by the earlier 576B OBJ.
                receipts=dict(read(folder/'returns904.json'))
                big=next(e for e in read(folder/'events.json') if e.get('generation')==906
                         and e.get('opcode')=='0xe8' and bytes.fromhex(e['reply'])[14:18]==(6).to_bytes(4,'little'))
                row['g906_576B']=dict(ready=by_job[906,6,1,576],E8=round(big['clock']),returned=receipts[6],
                                      next_ready=by_job[906,8,1,64])
                cases[mode]=row
    for mode in modes:
        cases=[group[mode] for group in data['cases'].values()]
        warm,cold=cases[:2],cases[2:]
        refs=[group['938'] for group in data['cases'].values()]
        link=data['links'][mode]
        link['gates']=dict(Flash=link['Flash']<=212992,
            earlier_64_and_352=all(row['token22']['ready']<ref['token22']['ready'] and
                row['token24_ready']<ref['token24_ready'] for row,ref in zip(cases,refs,strict=True)),
            warm13_and_before_OAM=all(row['total']==13 and row['before_OAM'] for row in warm),
            cold15_and_496=all(row['total']==15 and row['preSEAL']==496 and row['tail_DMA'] for row in cold),
            capture=all(row['capture_margin']>=0 for row in cases),
            supply_no_later_935=all(not row['late_vs935'] for row in cases),
            ACK_no_later_935=all(row['ACK_delta935']<=0 for row in cases),
            recovery_verified='guards' in link and len(link.get('priority_edges',{}))==4)
    return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.modes),indent=2)+'\n',encoding='utf8')
