# SPDX-License-Identifier: MIT
"""Join actual Gray register placement, per-bit STA, whole-board and consumer results."""
import argparse
import json
import re
from pathlib import Path
from analyze_nes_owner562 import board,read
from analyze_nes_reuse565 import table,pin_budget
from analyze_nes_start572 import delta
from nes_raw506 import sha


def epoch_paths(p):
    sites={r['name'].split('|')[-1]:r['site'] for r in table(p/'epoch573-sites.tsv')}
    assert len(sites)==96
    setup=table(p/'epoch568.tsv')
    hold={(r['corner'],r['to']):r for r in table(p/'epoch573-hold.tsv')}
    assert len(hold)==192
    paths={}
    for leg,source,dest in [('input','gray','epoch_meta'),('sync','epoch_meta','epoch_sync')]:
        report=(p/f'epoch573-{leg}.rpt').read_text(errors='replace')
        pins=dict(re.findall(r'content_lifetime\|'+dest+r'\[(\d+)\]\|(d|asdata)\s*;',report))
        assert len(pins)==32
        rows=[]
        for r in setup:
            if r['path']!=leg:continue
            bit=r['bit']
            src=f'{source}[{bit}]'
            dst=f'{dest}[{bit}]'
            h=hold[r['corner'],r['to']]
            assert h['from']==r['from'] and r['from'].endswith('|'+src) and r['to'].endswith('|'+dst)
            rows.append(dict(corner=r['corner'],bit=int(bit),source=sites[src],dest=sites[dst],
                             slow_0C_data_pin=pins[bit],setup_ns=float(r['slack']),hold_ns=float(h['slack']),
                             setup_data_delay_ns=float(r['data_delay']),hold_data_delay_ns=float(h['data_delay'])))
        assert len({(r['corner'],r['bit']) for r in rows})==96
        paths[leg]=rows
    return paths


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--traces',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    t=a.traces
    root=Path(__file__).resolve().parents[1]/'analysis'
    prior=read(root/'start572-verification.json')
    inputs=read(root/'trial558-verification.json')['inputs']
    base=t/'nes-start572-loader'
    folders={'MMC558':'nes-admit556-board01','570':'nes-gate570-board05','572':'nes-start572-loader',
             'mapping':'nes-epoch573-mapping','sampling':'nes-epoch573-sampling','pair':'nes-epoch573-pair02'}
    result={}
    for name,folder in folders.items():
        p=t/folder
        b=board(p)
        if name in ('MMC558','570','572'):
            assert b['SOF']==prior['boards']['loader' if name=='572' else name]['SOF']
        else:
            changed=sorted(k for k in inputs if sha(p/k)!=sha(base/k))
            expected=['nes_source_epoch207.sv']
            if name=='pair':
                expected=['board.qsf'] if 'board.qsf' in inputs else []
            assert changed==expected,changed
            assert all(sha(p/f)==sha(base/f) for f in ('board.sdc','nominal204.sdc','cdc181.sdc'))
            qs=(p/'board.qsf').read_text()
            if name=='pair':
                extra=qs.removeprefix((base/'board.qsf').read_text()).strip().splitlines()
                assert [x for x in extra if x]==[f'set_location_assignment FF_X26_Y22_N{n} -to nes_live_joint:core|nes_spi_boot:loader_boot|nes_source_epoch207:content_lifetime|{stage}[23]' for stage,n in [('epoch_meta',9),('epoch_sync',7)]]
            else:assert qs==(base/'board.qsf').read_text()
        paths=epoch_paths(p)
        result[name]=dict(SOF=b['SOF'],RTL=sha(p/'nes_source_epoch207.sv'),QSF=sha(p/'board.qsf'),fit=b['fit'],
            whole=b['worst'],rows=b['rows'],ucp=b['unconstrained'],epoch=paths,PSRAM_ns=pin_budget(p)['worst_ns'],
            ROM_OE={r['corner']:r['slack'] for r in table(p/'arg564-paths.tsv') if r['cut']=='OE'},
            vs558=delta(prior['boards']['MMC558']['rows'],b['rows']),vs570=delta(prior['boards']['570']['rows'],b['rows']))
    assert result['mapping']['rows']==result['572']['rows'] and result['mapping']['epoch']==result['572']['epoch']
    # Verify both requested sites actually took effect in the fitted netlist.
    for leg,key in [('input','dest'),('sync','dest')]:
        def bit23(n):
            return next(r[key] for r in result[n]['epoch'][leg] if r['bit']==23)
        assert bit23('pair')==bit23('MMC558')
    functional={}
    for m in ('base','mapping','sampling'):
        r=read(t/f'nes-epoch573-test02-{m}'/'result.json')
        p=base if m=='base' else t/f'nes-epoch573-{m}'
        assert r['reference']==sha(base/'nes_source_epoch207.sv') and all(sha(p/k)==v for k,v in r['modules'].items())
        functional[m]=r
        assert r['phases']==functional['base']['phases']
        assert r['exhaustion'] and r['missing_second_edge_rejected']==(m=='sampling')
    pins=read(t/'nes-epoch573-pins/result.json')
    for k in ('latency_ps','results','mux_cases'):
        assert pins[k]==prior['pins']['joint'][k]
    assert pins['top']==sha(base/'fxpak_nes_screen137_top.sv')
    for f,h in pins['modules'].items():
        assert all(sha(t/folders[n]/f)==h for n in ('572','mapping','sampling','pair'))
    for i,ph in enumerate(prior['schedule'],1):
        d=t/f'nes-epoch573-replay{i}'
        assert read(d/'audit.json')==ph['audit']
        for f in ('arrivals.tsv','window.csv','bank561.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
            assert sha(d/f)==sha(t/f'nes-start572-replay{i}'/f),f
    a.out.write_text(json.dumps(dict(boards=result,functional=functional,pins=pins,schedule=prior['schedule'],
        scope='Actual scrub/capture/lease with earliest eligible injected PPU event. Separate two-phase Mesen replay, prior fixed ARM/SPI/IRQ/ROM arrivals. No new physical FPS.'),indent=2)+'\n')


if __name__=='__main__':
    main()
