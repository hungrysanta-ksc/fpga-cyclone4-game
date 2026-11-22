"""Align 909 OAM, 910 receiver and 912 physical DMA against the same 935 phase."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from analyze_nes_chain935 import measure
from analyze_nes_deadline922 import measure as frame_times
from analyze_nes_palette921 import directory, read_csv, sha
from analyze_nes_rows931 import job_times
from nes_chain935 import fit_arm, output
from nes_wait936 import work
import analyze_nes_obj923 as obj
import analyze_nes_chain935 as chain


def analyze(temp, mode, phase, cache):
    tag = '936'+mode if mode != '935' else '935boundedfinal'
    arm = work(mode) if mode != '935' else fit_arm()
    folder = directory(temp, phase, tag, cache)
    ref = directory(temp, phase, '935boundedfinal', cache)
    stats = measure(temp,'bounded',phase,cache,tag=tag,trial=arm)
    timing, _ = frame_times(folder,arm)
    current, previous = job_times(folder), job_times(ref)
    assert current.keys()==previous.keys()
    later = [(t-previous[job],list(job)) for job,t in current.items()
             if job[:2] not in ((912,32),(912,35))]
    g909,g910=(timing['frames'][g] for g in (909,910))
    win = read_csv(folder,'window.csv')
    oam = next(r for r in win if r['g']=='909' and r['op']=='8' and r['event']=='load')
    prior_blank = int(next(r['frame'] for r in win if r['g']=='909' and r['event']=='reveal'))-1
    before_show = [dict(event=r['event'],op=int(r['op']),size=int(r['value']),line=int(r['line']))
                   for r in win if r['g']=='909' and int(r['frame'])==prior_blank and int(r['line'])>=224
                   and (r['event']=='ppu_dma' or r['op']=='8' and r['event'] in ('load','ack'))]
    assert g909['clocks']['show'] < g909['clocks']['ACK'] <= g909['clocks']['E0_response'] < g910['commit'] < g910['commit_D2']
    return dict(gaps=stats['gaps'],total=stats['intervals'],ACK912=stats['ACK'],
                ACK925=stats['ACK925'],early912=stats['bytes_in_target'],tail=stats['tail_grant'],
                other_count=len(later),later_vs935=sum(dt>0 for dt,_ in later),
                max_delta_vs935=max(later),later_vs933=stats['other_later'],
                capture_margin=-stats['D2_minus_reference_capture'],
                OAM909=int(oam['clock']),OAM909_line=int(oam['line']),previous_blank909=before_show,
                early909_B=sum(row[2] for row in g909['preDMA']),
                clocks909=g909['clocks'],capture_ready910=g910['capture_ready'],
                first_D1=g910['first_D1'],data_D2=g910['data_D2'],COMMIT=g910['commit'],
                final_D2=g910['commit_D2'])


def collect(temp,modes):
    result=dict(clock_Hz=21477272,physical=False,ROM_sha256=sha(output('bounded')/'sink165.sfc'),runs={})
    for mode in ('935',*modes):
        arm=fit_arm() if mode=='935' else work(mode)
        binary=arm/'link/src/obj-nes-100/firmware.stm'
        data=dict(sha256=sha(binary),Flash=binary.stat().st_size,cases={})
        result['runs'][mode]=data
        tag='935boundedfinal' if mode=='935' else '936'+mode
        if mode!='935' and (arm/'final-stops.json').exists():
            with patch.object(obj,'client',lambda _:output('bounded')), patch.object(chain,'fit_arm',lambda:arm):
                data['guards']=obj.recovery('final',arm,trial=arm)
                data['marker_cases']=chain.markers()
            for phase in (1,2):
                for case in ('head','stop'):
                    edge=directory(temp,phase,tag,'cold')/f'edge935-{case}-verified.json'
                    if edge.exists():
                        data.setdefault('edge_tests',{})[f'p{phase}-{case}']=json.loads(edge.read_bytes())
        for cache in ('warm','cold'):
            for phase in (1,2):
                if (directory(temp,phase,tag,cache)/'joint.json').exists():
                    data['cases'][f'{cache}{phase}']=analyze(temp,mode,phase,cache)
        if mode!='935' and len(data['cases'])==4:
            cases=data['cases']
            base=result['runs']['935']['cases']
            data['gates']=dict(
                warm_13=all(cases['warm'+str(p)]['total']==13 for p in (1,2)),
                earlier_warm_input=all(cases[k]['first_D1']<base[k]['first_D1'] and
                                       cases[k]['data_D2']<base[k]['data_D2'] for k in ('warm1','warm2')),
                warm_capture=all(cases[k]['capture_margin']>=0 for k in ('warm1','warm2')),
                cold_496_and_15=all(cases[k]['early912']==496 and cases[k]['tail'] and
                                    cases[k]['total']==15 for k in ('cold1','cold2')),
                other_tiles_on_time=all(not case['later_vs935'] for case in cases.values()),
                final_ACK_on_time=all(case['ACK912']<=base[k]['ACK912'] for k,case in cases.items()),
                Flash_fit=data['Flash']<=212992)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('modes',nargs='+')
    args=parser.parse_args()
    args.out.write_text(json.dumps(collect(args.temp,args.modes),indent=2)+'\n',encoding='utf-8')
