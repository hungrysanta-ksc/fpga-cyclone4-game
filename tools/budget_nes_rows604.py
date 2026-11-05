"""Align each measured first E9 with the final grant of the preceding boot-calendar window."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path

from analyze_nes_wire600 import MASTER, INPUT
from check_nes_wire600 import ROOT, read, pin
from test_nes_service509_schedule import Calendar


def compare(a):
    sim=read(ROOT/'analysis/rows604-verification.json')
    base=read(ROOT/'analysis/wire600-verification.json')
    cal=Calendar(a.calendar)
    result=[]
    for old,new,q in zip(sim['shared']['frames'],sim['rows']['frames'],base['phases'],strict=True):
        phase,g=new['phase'],new['generation']
        assert all((r['phase'],r['generation'])==(phase,g) for r in (old,q))
        p=read(ROOT/'analysis/whole580-verification.json')['phases'][phase-1]
        assert cal.summary==p['parameters']['ROM_calendar']
        shift=p['parameters']['ROM_phase']
        folder=a.traces/f'nes-close561-run{phase}'
        for f in ('events.json','obj-phases.json'):pin(folder/f,p['evidence'][f])
        origin=next(e['clock'] for e in read(folder/'events.json') if e['generation']==g and e['event']=='source_begin')
        marks=read(folder/'obj-phases.json')[str(g)]
        decode=marks['first_BG561']-marks['banks557'][0]['seal']
        request=origin+new['first_BG']['end_ns']*MASTER/1e9+decode
        grant,_=cal.select(request-shift)
        epoch,offset=divmod(grant,cal.period)
        pos=bisect_left(cal.starts,offset)
        previous=(epoch-int(pos==0))*cal.period+cal.starts[pos-1]+shift
        assert previous<request<=grant+shift
        assert abs((grant+shift-origin)*1000/MASTER-new['first_ROM_grant_ms'])<1e-8
        ref_B=sum(old['wire'][k] for k in INPUT)
        new_B=sum(new['wire'][k] for k in INPUT)
        assert ref_B-new_B==278 and new['blocks']==14 and old['blocks']==15
        # Replace only the optimistic receiver traffic inside stage 600's mixed floor.
        mixed=q['wire_floor_B']-sum(base['receiver'][str(g)]['shared']['wire'].values())+new_B
        result.append(dict(phase=phase,generation=g,control_input_B=ref_B,input_B=new_B,
                    saved_B=ref_B-new_B,modeled_first_BG_gain_ms=(old['first_BG']['end_ns']-new['first_BG']['end_ns'])/1e6,
                    first_grant_gain_ms=old['first_ROM_grant_ms']-new['first_ROM_grant_ms'],
                    prior_window_last_E9_end_ms=(previous-origin-decode)*1000/MASTER,
                    extra_advance_for_one_prior_grant_ms=(request-previous)*1000/MASTER,
                    live_input_plus_stage600_output_floor_B=mixed))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('traces','calendar','out'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    a.out.write_bytes((json.dumps(compare(a),indent=2)+'\n').encode())
