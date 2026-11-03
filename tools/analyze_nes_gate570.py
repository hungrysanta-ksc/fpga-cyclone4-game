# SPDX-License-Identifier: MIT
"""Reconcile the three routed controls with the fault injections, plan credit and display replays."""
import argparse
from collections import Counter
import re
import json
from pathlib import Path
from analyze_nes_owner562 import board,read
from analyze_nes_reuse565 import table,pin_budget
from nes_raw506 import sha


def output_inventory(folder,view):
    report=(folder/(view+'-unconstrained204.rpt')).read_text()
    sections=re.split(r'(?m)^; Unconstrained Output Port Paths *; *$',report)[1:]
    assert len(sections)==2
    totals=[]
    for section in sections:
        lines=section.splitlines()
        header=next(i for i,line in enumerate(lines) if line.startswith(';') and 'Clock' in line)
        counts=Counter()
        for line in lines[header+2:]:
            if not line.startswith(';'):break
            fields=[f.strip() for f in line.strip('; ').split(';')]
            counts[fields[1]]+=1
        totals.append(counts)
    return totals


def analyze(a):
    root=Path(__file__).resolve().parents[1]/'analysis'
    prior=read(root/'plan569-verification.json')
    base=a.traces/'nes-plan569-board01'
    assert sha(base/'output_files/board.sof')==prior['boards']['end_only']['candidate']['SOF']
    physical=read(root/'owner562-verification.json')['boards']['MMC558']
    inputs=read(root/'trial558-verification.json')['inputs']
    fulltest=read(a.rtl/'result.json');wire=read(a.wire/'result.json')
    fulltest.update(read(a.shared/'result.json'));wire.update(read(a.shared_wire/'result.json'))
    fulltest.update(read(a.local/'result.json'));wire.update(read(a.local_wire/'result.json'))
    for name,cases in fulltest.items():
        assert len(cases['phases'])==len(wire[name])==2
        for i,phase in enumerate(cases['phases']):
            assert phase['E8']==8 and phase['E9']==3 and len(phase['loss_ps'])==6
            assert phase['loss_ps']==fulltest['base']['phases'][i]['loss_ps']
            assert wire[name][i]['allow_ps']==wire['base'][i]['allow_ps']
            assert wire[name][i]['common_reset_while_stopped']
            if name in ('joint','shared','local'):
                assert wire[name][i]['bulk']==[dict(partial=0,consumes=1),dict(partial=1,consumes=0)]
                assert wire[name][i]['e8']==[['80','0'],['01','0']]
    out=dict(boards={},functional=fulltest,observers=wire,replays=[])
    for name,dirname,proof in [('base','nes-plan569-board01','base'),('transport','nes-gate570-board01','transport'),
                               ('memory','nes-gate570-board02',None),('joint','nes-gate570-board03','joint'),('shared','nes-gate570-board04','shared'),('local','nes-gate570-board05','local')]:
        d=a.traces/dirname
        # The memory-only control uses the reference direct join and the
        # tested joint guard. Verify every functional RTL dependency.
        for f,h in fulltest[proof or 'base']['modules'].items():
            if proof is None and f=='nes_diag_clock_guard127.sv':h=fulltest['joint']['modules'][f]
            assert sha(d/f)==h,(d,f)
        for f in ('board.sdc','nominal204.sdc','board.qsf','cdc181.sdc'):assert sha(d/f)==sha(base/f)
        changed={f:sha(d/f) for f in inputs if sha(d/f)!=sha(base/f)}
        expected={'nes_diag_clock_guard127.sv'} if name!='base' else set()
        if name in ('transport','joint','shared','local'):expected.add('nes_direct206.sv')
        assert changed.keys()==expected
        b=board(d);old=physical['rows']
        assert old.keys()==b['rows'].keys()
        regress={k:[old[k],v] for k,v in b['rows'].items() if v[0]<min(0,old[k][0])}
        related=all(b['fit'][v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
        ucp=b['unconstrained'];orig=physical['unconstrained']
        assert ucp.keys()==orig.keys() and all(x.keys()==orig[v].keys() for v,x in ucp.items())
        no_growth=all(len(row)==len(orig[v][k]) and all(n<=o for n,o in zip(row,orig[v][k]))
                      for v,x in ucp.items() for k,row in x.items())
        pins=pin_budget(d)
        routed=table(d/'arg564-paths.tsv')
        oe={r['corner']:float(r['slack']) for r in routed if r['cut']=='OE'}
        path=table(d/'gate570.tsv');inv=table(d/'gate570-registers.tsv')[0]
        assert len(oe)==3 and all(int(inv[k])>=1 for k in ('ref','release','nf','parent','plan','meta'))
        assert int(inv['stage'])==(0 if name=='base' else 2)
        def present(tag,expect):
            slacks=[r['slack'] for r in path if r['path']==tag]
            assert len(slacks)==3 and all((s!='NONE')==expect for s in slacks),(name,tag,slacks)
        present('ref_release',name=='base')
        present('ref_stage',name!='base')
        present('nf_plan',name in ('base','memory'))
        present('parent_plan',name in ('transport','joint','shared','local'))
        for k in ('nf_parent','memory_fault'):present(k,True)
        assert int(inv['bank'])>0
        present('nf_bank',name not in ('shared','local'))
        present('parent_bank',name in ('shared','local'))
        ports={}
        for view in ucp:
            cur=output_inventory(d,view);ref=output_inventory(base,view)
            assert [sum(c.values()) for c in cur]==ucp[view]['Unconstrained Output Port Paths']
            ports[view]=[{pin:c[pin]-r[pin] for pin in sorted(c.keys()|r.keys()) if c[pin]!=r[pin]} for c,r in zip(cur,ref)]
        if name in ('shared','local'):
            assert int(inv['plan_hr'])==2
            present('core_plan_hr',name=='shared')
            present('parent_plan_hr',True)
        gate=related and not regress and no_growth and pins['worst_ns']>0 and min(oe.values())>=0
        out['boards'][name]=dict(changes=changed,board=b,output_path_deltas_vs569=ports,clock_paths=path,inventory=inv,global_endpoints=routed,
            regressions=regress,tns_worse={k:[old[k][1],v[1]] for k,v in b['rows'].items() if v[1]<old[k][1]},related_pass=related,no_ucp_growth=no_growth,OE=oe,pins=pins,
            board_gate=gate,trial_gate=gate and name in ('joint','shared','local'))
    out['SNES_output_legs']={}
    for name,dirname in [('MMC558','nes-admit556-board01'),('base','nes-plan569-board01'),('local','nes-gate570-board05')]:
        legs=table(a.traces/dirname/'snes570.tsv')
        for c in {r['corner'] for r in legs}:
            host=[r for r in legs if r['corner']==c and r['leg']=='host']
            extra=[r for r in legs if r['corner']==c and r['leg']=='plan_release']
            assert len(host)==10 and len(extra)==(10 if name=='local' else 0)
            assert len({r['to'] for r in host})==10
        out['SNES_output_legs'][name]=legs
    for i,ph in enumerate(prior['replays'],1):
        ref=a.traces/f'nes-plan569-play{i}';d=a.traces/f'nes-gate570-play{i}'
        assert read(d/'audit.json')==ph['audit']
        for f in ('arrivals.tsv','window.csv','bank561.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
            assert sha(d/f)==sha(ref/f),f
        out['replays'].append(ph)
    out['scope']='Separate clock-guard and production direct-path RTL fault injections, actual E8/E9 and two clock phases. External tile completion for scheduled 954; existing ARM/IRQ/ROM arrivals and actual 65816 for 53 displays. No electrical shutdown latency or new physical FPS measurement.'
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('rtl','wire','shared','shared_wire','local','local_wire','traces','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
