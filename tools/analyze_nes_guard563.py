# SPDX-License-Identifier: MIT
"""Reconcile clock-loss tests, fitted bus timing, full STA and 53-screen replay."""
import argparse
import csv
import json
import re
from pathlib import Path
from analyze_nes_owner562 import board,read
from nes_raw506 import sha


def timing_inventory(folder):
    with (folder/'capture563.tsv').open() as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    report=(folder/'output_files/board.map.rpt').read_text(errors='replace')
    alias=re.search(r'\|address_hold\[20\]\s*; Merged with [^\n;]+\|address_hold\[19\]\s*;',report)
    assert alias
    def coords(r):
        return [float(r[k]) for k in ('slack','launch','latch','arrival','required')]
    corners={}
    for c in sorted({r['corner'] for r in rows}):
        get=lambda view,cut:[r for r in rows if (r['view'],r['corner'],r['cut'])==(view,c,cut)]
        original=get('original','data')
        shadow=get('toggle_inventory','data')
        by_reg=lambda group:{r['from']:(r['to'],coords(r)) for r in group}
        assert by_reg(original)==by_reg(shadow)
        limits={}
        for row in original:
            bit=int(re.search(r'address_hold\[(\d+)\]$',row['from'])[1])
            slack,launch,latch,arrival,required=coords(row)
            assert abs(required-arrival-slack)<0.003
            limits[bit]=round(latch-launch-slack,3)
        assert set(limits)==set(range(22))-{20}
        assert not get('original','toggle')
        toggle,=get('toggle_inventory','toggle')
        assert toggle['to'].endswith('request_sync[0]')
        slack,launch,latch,arrival,required=coords(toggle)
        assert abs(arrival-required-slack)<0.003
        earliest=round(latch-launch+slack,3)
        period=float(toggle['period'])
        latest=max(limits.values())
        corners[c]=dict(min_first_sample_edge=earliest,latest_data_required=latest,
                        relative_setup_by_fitted_source_ns=limits,mem_period=period,
                        same_corner_margin_ns=round(earliest+2*period-latest,3))
    assert len(corners)==3
    early=min(x['min_first_sample_edge'] for x in corners.values())
    late=max(x['latest_data_required'] for x in corners.values())
    periods={x['mem_period'] for x in corners.values()};assert len(periods)==1
    return dict(corners=corners,alias='address_hold[20] merged into [19]',
                mixed_corner_margin_ns=round(early+2*periods.pop()-late,3),
                path_report_SHA256=sha(folder/'capture563.tsv'),
                guard_and_host=[r for r in rows if r['cut'].startswith(('guard_','host_'))])


def analyze(a):
    root=Path(__file__).resolve().parents[1]
    prior=read(root/'analysis/owner562-verification.json')
    old=prior['boards']['562']
    assert sha(a.base/'output_files/board.sof')==old['SOF']
    result=board(a.board)
    pins=read(root/'analysis/trial558-verification.json')['inputs']
    changes=sorted(n for n in pins if sha(a.base/n)!=sha(a.board/n))
    assert changes==['nes_diag_clock_guard127.sv','nes_live_joint.sv']
    original=prior['boards']['MMC558']['rows'];rows=result['rows']
    assert rows.keys()==original.keys()
    regress={k:[original[k],v] for k,v in rows.items() if v[0]<min(original[k][0],0)}
    checks=read(a.rtl/'result.json')
    phases=[]
    for i in (0,1):
        healthy=[]
        for name in ('original','split'):
            log=(a.rtl/name/f'phase{i}.log').read_text(errors='replace')
            assert 'PASS563 6 losses and common reset' in log
            events=re.findall(r'^# ((?:START563|REPLY563|CAPTURE563|LOSS563) .+)$',log,re.M)
            assert all(r.startswith('CAPTURE563 2 ') for r in events if r.startswith('CAPTURE563'))
            assert len([r for r in events if r.startswith('CAPTURE563')])==7
            healthy.append(events)
        assert healthy[0]==healthy[1] and checks[f'original{i}']==checks[f'split{i}']
        trace=a.traces/f'nes-owner562-run{i+1}';audit=a.traces/f'nes-guard563-replay{i+1}'
        observed=read(audit/'audit.json')
        p=prior['phases'][i]
        assert observed['frames']==53 and sha(trace/'window.csv')==observed['trace']==p['pins']['window.csv']
        for g in range(905,958):assert sha(trace/f'frame-{g}.rgb')==sha(audit/f'frame-{g}.rgb')
        phases.append(dict(start=p['start'],display_source='562 arrival schedule; independent 65816 replay',
                           audit=observed,dense_VB=p['dense_VB'],dense_ms=p['dense_ms'],last_ACK=p['last_ACK'],
                           waits=p['waits'],wait957=p['wait957'],fault_and_read_events=healthy[1]))
    inventories=[timing_inventory(d) for d in (a.base,a.board)]
    capture_pass=inventories[1]['mixed_corner_margin_ns']>0
    guards=inventories[1]['guard_and_host']
    assert not any(r['cut']=='guard_ref_qualified_recovery' for r in guards)
    assert len([r for r in guards if r['cut']=='guard_ref_qualified_setup'])==3
    assert len([r for r in guards if r['cut']=='guard_ref_fault_recovery'])==3
    fit=result['fit']
    local=all(fit[v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
    return dict(changed={n:sha(a.board/n) for n in changes},guard_cases=checks,phases=phases,board=result,
                capture562=inventories[0],capture563=inventories[1],negative_STA_regressions=regress,
                unchanged_unconstrained=result['unconstrained']==old['unconstrained'],related_STA_pass=local,
                capture_pass=capture_pass,
                trial_gate=local and capture_pass and not regress and result['unconstrained']==old['unconstrained'])


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','board','rtl','traces','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
