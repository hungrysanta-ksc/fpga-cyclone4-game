"""Correlate capture offer, D0/D1/D2, release of the previous display and the next BEGIN."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_obj923 as obj
from analyze_nes_oam937 import ordinary_packets
from analyze_nes_palette921 import directory, read, read_csv, sha
from analyze_nes_rows931 import job_times
from analyze_nes_wait936 import analyze
from nes_chain935 import output
from nes_input940 import MODES, work


def timeline(folder,generation):
    events=read(folder/'events.json')
    shown=next(int(row['clock']) for row in read_csv(folder,'window.csv')
               if int(row['g'])==generation-1 and row['event']=='reveal')
    begin=next(e for e in events if e.get('generation')==generation and e['event']=='source_begin')
    planner=next(e for e in events if e.get('generation')==generation and e['event']=='planner_enter')
    spi=[e for e in events if e['event']=='SPI' and e['clock']<=planner['clock']]
    inputs=[e for e in spi if e.get('input_generation')==generation]
    reads=[e for e in inputs if e['opcode']=='0xd1']
    pops=[e for e in inputs if e['opcode']=='0xd2']
    commit=next(e for e in inputs if e['opcode']=='0xd3')
    ea=next(e for e in spi if e.get('generation')==generation-1 and e['opcode']=='0xea')
    before=[e for e in spi if e['clock']<=reads[0]['start'] and e['start']>=begin['clock']-1]
    assert len(pops)==len(reads) and pops[-2]['clock']<commit['clock']<pops[-1]['clock']
    assert ea['clock']<commit['start'] and shown<=ea['start']
    begin_packet=next(e for e in spi if e['start']>pops[-1]['clock'] and e['opcode']=='0xe1' and e['packet_opcode']==1)
    first_d0=next(e for e in inputs if e['opcode']=='0xd0')
    service=[round(pop['start']-d1['clock']) for d1,pop in zip(reads,pops,strict=True)]
    assert min(service)>=0
    return dict(capture=round(begin['capture_ready']),previous_reveal=shown,begin=round(begin['clock']),
        first_D0_end=round(first_d0['clock']),first_D1=round(reads[0]['clock']),data_D2=round(pops[-2]['clock']),EA=round(ea['clock']),
        COMMIT=round(commit['clock']),commit_D2=round(pops[-1]['clock']),planner=round(planner['clock']),
        begin_to_planner=round(planner['clock']-begin['clock']),begin_minus_show=round(begin['clock']-shown),
        BEGIN_E1=round(begin_packet['clock']),D1_end_to_D2_start=service,
        BEGIN_E0_polls=sum(e['opcode']=='0xe0' and e['start']>begin_packet['clock'] for e in spi),
        wire_before_first_read=[e['opcode'] for e in before],payloads=[e['bytes']-3 for e in reads],
        busy_first=any(e['event']=='sender652_busy' and e.get('input_generation')==generation
                       and e['clock']<=reads[0]['start'] for e in events))


def report(temp,modes):
    refdata=read(Path(__file__).resolve().parents[1]/'analysis/wait936-results.json')['runs']['935']['cases']
    out=dict(clock_Hz=21477272,physical=False,consumer=sha(output('bounded')/'sink165.sfc'),cases={},links={})
    for mode in modes:
        arm=work(mode)
        fw=arm/'link/src/obj-nes-100/firmware.stm'
        link=out['links'][mode]=dict(Flash=fw.stat().st_size,firmware=sha(fw))
        if (arm/'decode940.json').exists():
            link['decoder_checks']=read(arm/'decode940.json')
            assert link['decoder_checks']['firmware']==link['firmware']
        if (arm/'dispatch938.json').exists():
            link['dispatch']=read(arm/'dispatch938.json')
            assert link['dispatch']['firmware']==link['firmware']
        if (arm/'final-stops.json').exists():
            with patch.object(obj,'client',lambda _:output('bounded')):
                link['recovery']=obj.recovery('final',arm,trial=arm)
            link['priority_edges']={}
            for ph in (1,2):
                for edge in ('head','stop'):
                    file=directory(temp,ph,'940'+mode,'cold')/f'edge935-{edge}-verified.json'
                    if file.exists():link['priority_edges'][f'{ph}-{edge}']=read(file)
    for cache in ('warm','cold'):
        for phase in (1,2):
            key=f'{cache}{phase}'
            group=out['cases'][key]={}
            ref,old,base=[directory(temp,phase,tag,cache) for tag in ('935boundedfinal','938fit','939tile')]
            tiles,old_tiles,base_tiles=map(job_times,(ref,old,base))
            ordinary=ordinary_packets(base)
            for name,folder in [('935',ref),('939',base),*((m,directory(temp,phase,'940'+m,cache)) for m in modes)]:
                row=group[name]={g:timeline(folder,g) for g in (909,911)}
                last_bank=read(folder/'banks904.json')['906']['banks557'][-1]
                row['last_plan906']={k:round(last_bank[k]) for k in ('first','count','seal','first_check','release')}
                if name in ('935','939'):continue
                for g in (909,911):assert row[g]['payloads']==group['939'][g]['payloads']
                assert ordinary==ordinary_packets(folder)
                stat=analyze(temp,name,phase,cache,tag='940'+name,arm=work(name))
                current=job_times(folder)
                assert current.keys()==tiles.keys()
                if name=='control':
                    assert row==group['939'] and current==base_tiles
                    assert read_csv(folder,'window.csv')==read_csv(base,'window.csv')
                row['late_vs935']=[(k,v-tiles[k]) for k,v in current.items()
                                  if v>tiles[k] and k[:2] not in ((912,32),(912,35))]
                assert len(row['late_vs935'])==stat['later_vs935']
                jobs=[(909,22,1,64),(909,24,1,352)]
                row.update(gaps=stat['gaps'],total=stat['total'],preSEAL=stat['early912'],tail=stat['tail'],
                           capture_margin=stat['capture_margin'],ACK=stat['ACK912'],ACK_delta935=stat['ACK912']-refdata[key]['ACK912'],
                           OBJ_delta938=[current[k]-old_tiles[k] for k in jobs],
                           OBJ_delta939=[current[k]-base_tiles[k] for k in jobs])
    for mode in modes:
        link=out['links'][mode]
        cases=[group[mode] for group in out['cases'].values()]
        w=out['cases']['warm1']
        c=out['cases']['cold2']
        link['gates']=dict(fits=link['Flash']<=212992,
            earlier_warm909=w[mode][909]['begin']<w['939'][909]['begin'],
            warm909_vs_display=w[mode][909]['begin_minus_show']<w['939'][909]['begin_minus_show'],
            earlier_warm909_first_D1=w[mode][909]['first_D1']<w['939'][909]['first_D1'],
            earlier_warm909_planner=w[mode][909]['planner']<w['939'][909]['planner'],
            shorter_cold911=c[mode][911]['begin_to_planner']<c['939'][911]['begin_to_planner'],
            earlier_cold911_planner=c[mode][911]['planner']<c['939'][911]['planner'],
            warm13=all(r['total']==13 for r in cases[:2]),
            cold496_and_15=all(r['total']==15 and r['tail'] and r['preSEAL']==496 for r in cases[2:]),
            capture=all(r['capture_margin']>=0 for r in cases),
            OBJ_gains_over_938=all(max(r['OBJ_delta938'])<0 for r in cases),
            OBJ_no_later_than_939=all(max(r['OBJ_delta939'])<=0 for r in cases),
            all_other_tiles_935=all(not r['late_vs935'] for r in cases),
            final_ACK_935=all(r['ACK_delta935']<=0 for r in cases),
            guards='dispatch' in link and 'recovery' in link and len(link.get('priority_edges',{}))==4)
        link['all_requested_gates']=all(link['gates'].values())
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.modes),indent=2)+'\n',encoding='utf8')
