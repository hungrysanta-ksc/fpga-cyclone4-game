# SPDX-License-Identifier: MIT
"""Reconcile routed PSRAM legs, reset-release edges and the actual SNES token writes."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
from analyze_nes_owner562 import board,read
from nes_raw506 import sha


def table(p):
    with p.open() as f:return list(csv.DictReader(f,delimiter='\t'))


def pin_budget(d):
    rows=table(d/'pins565.tsv')
    def leg(r):
        return round(float(r['latch'])-float(r['launch'])-float(r['slack']),3)
    corners={}
    for c in sorted({r['corner'] for r in rows}):
        groups={key:[r for r in rows if r['corner']==c and r['leg']==key] for key in ('active','early','data')}
        active=groups['active'];data=groups['data']
        assert {r['to'] for r in active}=={'ROM_1CE','ROM_2CE','ROM_OE'}
        assert {r['from'] for r in data}=={f'ROM_DATA[{i}]' for i in range(16)}
        assert {r['to'] for r in groups['early']}=={f'ROM_ADDR[{i}]' for i in range(20)}|{r['to'] for r in active}
        a,b,ret=[max(map(leg,groups[k])) for k in ('early','active','data')]
        oe=next(leg(r) for r in active if r['to']=='ROM_OE')
        corners[c]=dict(early_leg_ns=a,active_leg_ns=b,OE_leg_ns=oe,data_leg_ns=ret,
                        early_margin_ns=round(17*5.952-a-70-4-ret,3),
                        active_margin_ns=round(16*5.952-b-70-4-ret,3),
                        OE_margin_ns=round(16*5.952-oe-70-4-ret,3))
    assert len(corners)==3
    return dict(corners=corners,period_ns=5.952,PSRAM_ns=70,PCB_each_way_ns=2,
                worst_ns=min(min(v['early_margin_ns'],v['active_margin_ns']) for v in corners.values()),
                paths=sha(d/'pins565.tsv'),resets=table(d/'reset565.tsv'))


def traffic(d):
    groups=defaultdict(list)
    with (d/'bank561.csv').open() as f:
        for row in csv.DictReader(f):groups[int(row['index'])].append(row)
    maxima={};first={}
    for index,g in groups.items():
        assert [r['event'] for r in g]==['descriptor','last_read','token0','token1','token2','token3','consume']
        stamps=[int(r['clock']) for r in g]
        assert stamps==sorted(stamps) and len({(r['bytes'],r['token']) for r in g})==1
        for j in (0,1,2):
            label=g[j]['event']
            span=stamps[-1]-stamps[j]
            if span>maxima.get(label,{}).get('ticks',-1):maxima[label]=dict(index=index,ticks=span,us=round(span/21.477272,3))
            if int(g[0]['token'])==1:first[label]=span
    assert len(groups)==121 and len(first)==3
    return dict(jobs=len(groups),max_to_consume=maxima,first_token_ticks=first,events=sha(d/'bank561.csv'))


def analyze(a):
    root=Path(__file__).resolve().parents[1]
    prior=read(root/'analysis/arg564-verification.json')
    pins=read(root/'analysis/trial558-verification.json')['inputs']
    changed=sorted(k for k in pins if sha(a.base/k)!=sha(a.board/k))
    assert changed==['nes_rom_boot.sv','nes_tile_bulk206.sv'] and sha(a.base/'output_files/board.sof')==prior['board']['SOF']
    budgets={name:pin_budget(d) for name,d in [('558',a.physical),('564',a.base),('565',a.board)]}
    assert sum(r['cut']=='core_cancel' for r in budgets['564']['resets'])==3
    assert not any(r['cut']=='core_cancel' for r in budgets['565']['resets'])
    full=board(a.board);control=read(root/'analysis/owner562-verification.json')['boards']['MMC558']
    rows=full['rows'];original=control['rows'];assert rows.keys()==original.keys()
    regress={k:[original[k],r] for k,r in rows.items() if r[0]<min(0,original[k][0])}
    rtl=read(a.rtl/'result.json');base=rtl['564'];new=rtl['565']
    assert new['samples']==base['samples']==974 and new['bus']==base['bus'] and new['events']==base['events']==1930
    for i in (0,1):
        for mode in ('clean','partial','replay'):
            k=mode+str(i)
            assert base['banks'][k]==[5,204,255,int(mode=='replay')]
            assert new['banks'][k]==[7,204,255,int(mode=='replay')]
    replay=[]
    for i,p in enumerate(prior['phases'],1):
        audit=a.traces/f'nes-reuse565-bus{i}';trace=a.traces/f'nes-owner562-run{i}'
        verification=read(audit/'audit.json')
        assert verification==p['replay']
        for g in range(905,958):assert sha(audit/f'frame-{g}.rgb')==sha(trace/f'frame-{g}.rgb')
        replay.append(dict(phase=i,traffic=traffic(audit),audit=verification,dense_ms=p['dense_ms'],dense_VB=p['dense_VB'],
                           final_ACK=p['final_ACK'],wait957=p['wait957']))
    fit=full['fit']
    local=all(fit[v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
    replay_alias=all(new['banks']['replay'+str(i)][3]==1 for i in (0,1))
    same_ucp=full['unconstrained']==control['unconstrained']
    ucp=full['unconstrained'];old_ucp=control['unconstrained']
    assert ucp.keys()==old_ucp.keys() and all(ucp[v].keys()==old_ucp[v].keys() for v in ucp)
    no_growth=all(len(n)==len(old_ucp[v][k]) and all(a<=b for a,b in zip(n,old_ucp[v][k]))
                  for v in ucp for k,n in ucp[v].items())
    return dict(changed={k:sha(a.board/k) for k in changed},pin_budget=budgets,rtl=rtl,board=full,replay=replay,
                OE_original_STA=[r for r in table(a.board/'arg564-paths.tsv') if r['cut']=='OE'],
                regressions=regress,related_STA_pass=local,unchanged_unconstrained=same_ucp,no_ucp_growth=no_growth,
                stale_full_ACK_accepted=replay_alias,reset_bus_quiescence_proven=False,
                trial_gate=local and no_growth and not regress and not replay_alias and budgets['565']['worst_ns']>0,
                scope='Complete old ACK replay was injected at the RTL bus. Normal replay uses 562 arrivals and does not inject core reset.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('physical','base','board','rtl','traces','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
