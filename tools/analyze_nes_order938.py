"""Measure source, two-slot publication, consumer acceptance and bank return."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_obj923 as obj
from analyze_nes_oam937 import ordinary_packets
from analyze_nes_palette921 import directory, read, read_csv, sha
from analyze_nes_return930 import jobs
from analyze_nes_rows931 import job_times
from analyze_nes_wait936 import analyze
from nes_chain935 import output
from nes_order938 import work


def frame(folder):
    tiles=jobs(folder,(22,23,24),generation=909)
    rows=read_csv(folder,'window.csv')
    oam=next(r for r in rows if r['g']=='909' and r['event']=='load' and r['op']=='8')
    first=tiles[22]['clocks']
    tail=tiles[24]['clocks']
    return dict(OBJ64=first,OBJ352=tail,OAM_accept=int(oam['clock']),
                OBJ_before_fill=first['load']<int(oam['clock']),
                after_bank_return=tail['ready']-first['returned'])


def report(temp,modes):
    prior=read(Path(__file__).resolve().parents[1]/'analysis/wait936-results.json')['runs']['935']['cases']
    result=dict(clock_Hz=21477272,physical=False,ROM=sha(output('bounded')/'sink165.sfc'),runs={})
    for mode in modes:
        arm=work(mode)
        binary=arm/'link/src/obj-nes-100/firmware.stm'
        entry=dict(Flash=binary.stat().st_size,firmware=sha(binary),cases={})
        result['runs'][mode]=entry
        if (arm/'dispatch938.json').exists():
            entry['dispatch']=read(arm/'dispatch938.json')
            assert entry['dispatch']['firmware']==entry['firmware'] and len(entry['dispatch']['modes'])==6
        for cache in ('warm','cold'):
            for phase in (1,2):
                key=cache+str(phase)
                tag='938'+mode
                folder=directory(temp,phase,tag,cache)
                if not (folder/'joint.json').exists():
                    continue
                ref=directory(temp,phase,'937runs',cache)
                control=directory(temp,phase,'935boundedfinal',cache)
                assert ordinary_packets(folder)==ordinary_packets(ref)
                s=analyze(temp,mode,phase,cache,tag=tag,arm=arm)
                times=frame(folder)
                old=frame(ref)
                current,base=job_times(folder),job_times(control)
                assert current.keys()==base.keys()
                delays=[dict(job=k,clocks=v-base[k]) for k,v in current.items() if v>base[k]
                        and k[:2] not in ((912,32),(912,35))]
                s.update(times=times,return_delta937=times['OBJ64']['returned']-old['OBJ64']['returned'],
                         ready_delta937=times['OBJ352']['ready']-old['OBJ352']['ready'],
                         ACK_delta935=s['ACK912']-prior[key]['ACK912'],delayed_tiles_vs935=delays)
                assert len(delays)==s['later_vs935']
                receipts,baseline_receipts=[dict(read(d/'returns904.json')) for d in (folder,control)]
                # Earlier same-bank receipts identify lateness already present
                # before the OAM decision. Keep their absolute clocks.
                dependencies=[]
                for job,ready in current.items():
                    generation,token,_,_=job
                    if token in (8,22,24):
                        dependencies.append(dict(generation=generation,token=token,
                            previous_return=receipts[token-2],ready=ready,
                            baseline_return=baseline_receipts[token-2],baseline_ready=base[job]))
                s['bank_dependencies']=dependencies
                entry['cases'][key]={field:s[field] for field in (
                    'total','gaps','capture_margin','early912','tail','ACK912','ACK_delta935',
                    'return_delta937','ready_delta937','times','delayed_tiles_vs935',
                    'first_D1','data_D2','final_D2','clocks909','early909_B','bank_dependencies')}
        if (arm/'final-stops.json').exists():
            with patch.object(obj,'client',lambda _:output('bounded')):
                entry['recovery']=obj.recovery('final',arm,trial=arm)
        entry['priority_edges']={f'{p}-{kind}':read(edge) for p in (1,2) for kind in ('stop','head')
                     if (edge:=directory(temp,p,'938'+mode,'cold')/f'edge935-{kind}-verified.json').exists()}
        if len(entry['cases'])==4:
            warm=[entry['cases']['warm'+str(p)] for p in (1,2)]
            cold=[entry['cases']['cold'+str(p)] for p in (1,2)]
            entry['gates']=dict(Flash_fit=entry['Flash']<=212992,
                warm64_before_fill=all(s['times']['OBJ_before_fill'] for s in warm),
                warm_return_and_supply_earlier_than_937=all(max(s['ready_delta937'],s['return_delta937'])<0 for s in warm),
                warm13=all(s['total']==13 for s in warm),capture=all(s['capture_margin']>=0 for s in warm+cold),
                cold64_before_fill=all(s['times']['OBJ_before_fill'] for s in cold),
                cold15_and_496=all(s['total']==15 and s['early912']==496 and s['tail'] for s in cold),
                other_supply_no_later_than_935=all(not s['delayed_tiles_vs935'] for s in warm+cold),
                ACK_no_later_than_935=all(s['ACK_delta935']<=0 for s in warm+cold),
                both_priority_edges=len(entry['priority_edges'])==4,linked_recovery='recovery' in entry)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('modes',nargs='+')
    args=parser.parse_args()
    args.out.write_text(json.dumps(report(args.temp,args.modes),indent=2)+'\n',encoding='utf-8')
