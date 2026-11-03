# SPDX-License-Identifier: MIT
"""Reconcile original STA, pin routes, bus ownership tests and the two SNES schedules."""
import argparse
import json
from pathlib import Path
from analyze_nes_owner562 import board,read
from analyze_nes_reuse565 import table,pin_budget
from analyze_nes_gate570 import output_inventory
from nes_raw506 import sha


def pin_paths(folder):
    host=table(folder/'snes570.tsv')
    io=table(folder/'bus571.tsv')
    result={}
    for corner in sorted({r['corner'] for r in host}):
        def worst(rows):
            assert rows
            return max(rows,key=lambda r:float(r['delay'] if 'delay' in r else r['data_delay']))
        paths=[r for r in host if r['corner']==corner and r['leg']=='host']
        extra=[r for r in host if r['corner']==corner and r['leg']=='plan_release']
        assert len(paths)==10
        legs={}
        for group in ('SNES_READ_IN','SNES_WRITE_IN','SNES_ADDR_IN[*]','SNES_ROMSEL_IN'):
            rows=[r for r in io if r['corner']==corner and r['port_group']==group]
            legs[group]={pin:worst([r for r in rows if r['to']==pin]) for pin in sorted({r['to'] for r in rows})}
        result[corner]=dict(host=paths,plan_release=extra,controls=legs)
    assert len(result)==3
    return result


def main():
    p=argparse.ArgumentParser()
    for key in ('traces','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();t=a.traces
    analysis=Path(__file__).resolve().parents[1]/'analysis'
    old=read(analysis/'gate570-verification.json')
    keyset=read(analysis/'trial558-verification.json')['inputs']
    mmc=t/'nes-admit556-board01';ref=t/'nes-gate570-board05'
    assert old['boards']['local']['board']['SOF']==sha(ref/'output_files/board.sof')
    physical=read(analysis/'owner562-verification.json')['boards']['MMC558']
    out=dict(cases={},schedule=[],references={k:pin_paths(t/n) for k,n in [('558',mmc.name),('569','nes-plan569-board01'),('570',ref.name)]})
    detailed=(ref/'bus571-oe.rpt').read_text()
    assert '|bulk|aperture|enabled|' in detailed and 'hrelease|release_reset[1]|q' in detailed
    out['reference_OE_report']=sha(ref/'bus571-oe.rpt')
    refbench=read(t/'nes-bus571-signoffref/result.json')
    for name,idx,changed in [('aperture_reset','01',['nes_tile_bulk206.sv']),('read_mask','02',['nes_bulk_aperture188.sv']),
                             ('owner_mux','03',['fxpak_nes_screen137_top.sv','nes_tile_bulk206.sv'])]:
        folder=t/('nes-bus571-board'+idx)
        rtl=read(t/('nes-bus571-signoff'+idx)/'result.json')
        assert rtl['results']==refbench['results'] and rtl['mux_cases']==128
        assert rtl['latency_ps']==refbench['latency_ps'] and len(rtl['latency_ps'])==2
        assert rtl['top']==sha(folder/'fxpak_nes_screen137_top.sv')
        assert all(sha(folder/f)==h for f,h in rtl['modules'].items())
        assert sorted(k for k in keyset if sha(folder/k)!=sha(ref/k))==changed
        assert all(sha(folder/f)==sha(ref/f) for f in ('board.qsf','board.sdc','nominal204.sdc','cdc181.sdc'))
        full=board(folder)
        oldrows=physical['rows'];rows=full['rows']
        assert oldrows.keys()==rows.keys()
        regress={k:[oldrows[k],v] for k,v in rows.items() if v[0]<min(0,oldrows[k][0])}
        tns={k:[oldrows[k][1],v[1]] for k,v in rows.items() if v[1]<oldrows[k][1]}
        olducp=physical['unconstrained'];ucp=full['unconstrained']
        assert olducp.keys()==ucp.keys() and all(ucp[k].keys()==olducp[k].keys() for k in ucp)
        no_growth=all(len(r)==len(olducp[v][k]) and all(n<=o for n,o in zip(r,olducp[v][k]))
                      for v,x in ucp.items() for k,r in x.items())
        deltas={}
        for v in ucp:
            cur=output_inventory(folder,v);base=output_inventory(ref,v)
            assert [sum(x.values()) for x in cur]==ucp[v]['Unconstrained Output Port Paths']
            deltas[v]=[{n:c[n]-b[n] for n in sorted(c.keys()|b.keys()) if c[n]!=b[n]} for c,b in zip(cur,base)]
        related=all(full['fit'][v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
        pins=pin_budget(folder)
        ends=table(folder/'arg564-paths.tsv');oe={r['corner']:float(r['slack']) for r in ends if r['cut']=='OE'}
        assert len(oe)==3
        out['cases'][name]=dict(changed=changed,rtl=rtl,board=full,WNS_regression=regress,TNS_worse=tns,
            output_delta_vs570=deltas,legs=pin_paths(folder),global_endpoints=ends,OE_ns=oe,
            PSRAM=pins['worst_ns'],related_pass=related,no_ucp_growth=no_growth,
            board_gate=related and no_growth and not regress and min(oe.values())>=0 and pins['worst_ns']>0)
    for i,ph in enumerate(old['replays'],1):
        d=t/f'nes-bus571-play{i}';base=t/f'nes-gate570-play{i}'
        assert read(d/'audit.json')==ph['audit']
        for f in ('arrivals.tsv','window.csv','bank561.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
            assert sha(d/f)==sha(base/f),f
        out['schedule'].append(ph)
    out['scope']='Extracted board pin mux with real direct/sink/status RTL. Ideal IO report inventories routed paths, not measured external margins. Fixed prior ARM/IRQ/ROM arrivals, separately replayed 65816; no new physical FPS.'
    a.out.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':main()
