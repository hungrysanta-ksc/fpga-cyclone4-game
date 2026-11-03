# SPDX-License-Identifier: MIT
"""Check the two fitted alternatives against the same physical control and replay evidence."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_owner562 import board, read
from analyze_nes_reuse565 import pin_budget, table
from nes_raw506 import sha


def cost(folder, rtl, control, reference, inputs):
    changed = [n for n in inputs if sha(reference/n) != sha(folder/n)]
    assert changed == ['nes_native_mailbox165.sv'], changed
    constraints = {f.name:sha(f) for f in (reference/n for n in ('board.qsf','board.sdc','cdc181.sdc','nominal204.sdc'))}
    assert constraints and all(sha(folder/n)==digest for n,digest in constraints.items())
    case = read(rtl/'result.json')
    assert case['candidate'] == sha(folder/changed[0]) and case['base'] == sha(reference/changed[0])
    out = board(folder)
    old = control['rows']
    assert old.keys() == out['rows'].keys()
    regress = {k:[old[k],r] for k,r in out['rows'].items() if r[0] < min(0, old[k][0])}
    old_ucp = control['unconstrained']
    ucp = out['unconstrained']
    assert ucp.keys()==old_ucp.keys() and all(ucp[v].keys()==old_ucp[v].keys() for v in ucp)
    no_growth = all(len(x)==len(old_ucp[v][k]) and all(n<=b for n,b in zip(x,old_ucp[v][k]))
                    for v in ucp for k,x in ucp[v].items())
    psram = pin_budget(folder)
    oe = [r for r in table(folder/'arg564-paths.tsv') if r['cut']=='OE']
    assert len(oe)==3
    related = all(out['fit'][v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
    return dict(changed=changed,rtl=case,fit=out['fit'],worst=out['worst'],SOF=out['SOF'],STA=out['STA'],
                rows=out['rows'],regressions=regress,mailbox=table(folder/'mailbox567.tsv'),PSRAM=psram,
                OE=oe,unconstrained=ucp,no_ucp_growth=no_growth,related_pass=related,
                board_gate=not regress and related and no_growth and min(float(r['slack']) for r in oe)>=0 and psram['worst_ns']>0)


def schedule(root, phase, previous):
    run=root/f'nes-mailbox567-play{phase}'
    original=root/f'nes-reuse565-bus{phase}'
    assert read(run/'audit.json')==previous['audit']
    for name in ('arrivals.tsv','bank561.csv','window.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
        assert sha(run/name)==sha(original/name),name
    with (run/'window.csv').open() as f:rows=list(csv.DictReader(f))
    frames={int(r['g']):r for r in rows if r['event']=='reveal'}
    intervals={}
    for g in [952,957]:
        r=frames[g];old=frames[g-1]
        final=next(x for x in rows if int(x['g'])==g and x['event']=='final212')
        waits=sum(x['event']=='wait169' and int(x['g'])==g and int(x['clock'])>=int(final['clock']) for x in rows)
        intervals[g]=dict(interval_clocks=int(r['clock'])-int(old['clock']),VB=int(r['frame'])-int(old['frame']),waits=waits)
    last=int(next(r['clock'] for r in rows if r['event']=='ack' and r['g']=='957' and r['value']=='1'))
    assert last==previous['final_ACK']
    dense=sum(int(frames[g]['clock'])-int(frames[g-1]['clock']) for g in range(951,956))/5/21477.272
    assert abs(dense-previous['dense_ms'])<1e-6
    return dict(phase=phase,frames=len(frames),audit=read(run/'audit.json'),intervals=intervals,dense_ms=dense,
                last_ACK=last,arrivals=sha(run/'arrivals.tsv'),bank_events=sha(run/'bank561.csv'))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    analysis=Path(__file__).resolve().parents[1]/'analysis'
    prev=read(analysis/'reuse565-verification.json')
    control=read(analysis/'owner562-verification.json')['boards']['MMC558']
    base=a.traces/'nes-reuse565-board01'
    assert sha(base/'output_files/board.sof')==prev['board']['SOF']
    inputs=read(analysis/'trial558-verification.json')['inputs']
    results={name:cost(a.traces/('nes-mailbox567-board'+b),a.traces/('nes-mailbox567-rtl'+r),control,base,inputs)
             for name,b,r in [('receiver','01','02'),('local_ports','03','04')]}
    results['reference_paths']=table(base/'mailbox567.tsv')
    def endpoint(rows, key):
        values=[r['slack'] for r in rows if r['path']==key]
        assert len(values)==3
        return values
    for key in ('reset_valid','reset_prepared'):
        assert all(x!='NONE' for x in endpoint(results['reference_paths'],key))
        assert endpoint(results['local_ports']['mailbox'],key)==['NONE']*3
    assert all(float(x)>0 for x in endpoint(results['local_ports']['mailbox'],'other_valid'))
    results['replays']=[schedule(a.traces,i,old) for i,old in enumerate(prev['replay'],1)]
    results['scope']='Clock-edge RTL comparison for the changed mailbox, plus an independent actual 65816 replay of two existing ARM/IRQ/ROM schedules. No new board measurement or integrated ARM rerun.'
    a.out.write_text(json.dumps(results,indent=2)+'\n')
