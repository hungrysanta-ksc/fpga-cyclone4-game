# SPDX-License-Identifier: MIT
"""Compare original full-board slack rows, focused physical paths and cycle-matched behavior."""
import argparse
import json
from pathlib import Path
from analyze_nes_owner562 import board, read
from analyze_nes_reuse565 import pin_budget, table
from nes_raw506 import sha


def delta(reference, current):
    assert reference.keys() == current.keys()
    return {
        'WNS': {k: [reference[k][0], v[0]] for k, v in current.items() if v[0] < min(0, reference[k][0])},
        'TNS': {k: [reference[k][1], v[1]] for k, v in current.items() if v[1] < reference[k][1]}
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--traces', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / 'analysis'
    t = a.traces
    prior = read(root/'bus571-verification.json')
    maps = {'MMC558':'nes-admit556-board01', '570':'nes-gate570-board05', '571A':'nes-bus571-board01',
            **{name:'nes-start572-'+name for name in ('loader','memory','joint','revocable')}}
    evidence = {name:board(t/folder) for name,folder in maps.items()}
    expected_sof = [read(root/'owner562-verification.json')['boards']['MMC558']['SOF'],
                    read(root/'gate570-verification.json')['boards']['local']['board']['SOF'],
                    prior['cases']['aperture_reset']['board']['SOF']]
    assert [evidence[k]['SOF'] for k in ('MMC558','570','571A')] == expected_sof
    base = t/maps['571A']
    inputs = read(root/'trial558-verification.json')['inputs']
    changed = {'loader':['nes_rom_spi.sv'], 'memory':['nes_diag_clock_guard127.sv','nes_live_joint.sv']}
    changed['joint'] = changed['revocable'] = sorted(changed['loader'] + changed['memory'])
    boards = {}
    for name,folder in maps.items():
        p = t / folder
        b = evidence[name]
        actual = sorted(f for f in inputs if sha(p/f)!=sha(base/f))
        if name in changed:
            assert actual==changed[name]
            assert all(sha(p/f)==sha(base/f) for f in ('board.qsf','board.sdc','nominal204.sdc','cdc181.sdc'))
        mem_setup = [r for r in table(p/'implementation-paths204.tsv')
                     if r['kind']=='setup' and r['to_clock'].endswith('pll1|clk[1]')]
        corners = sorted({r['corner'] for r in mem_setup})
        assert len(corners)==3
        boards[name] = dict(fit=b['fit'],SOF=b['SOF'],whole=b['worst'],rows=b['rows'],ucp=b['unconstrained'],
                            memory_setup={c:min((r for r in mem_setup if r['corner']==c),
                                                key=lambda r:float(r['slack'])) for c in corners},
                            vs558=delta(evidence['MMC558']['rows'],b['rows']),vs570=delta(evidence['570']['rows'],b['rows']),
                            paths=table(p/'start572.tsv'),PSRAM_ns=pin_budget(p)['worst_ns'],
                            ROM_OE={r['corner']:r['slack'] for r in table(p/'arg564-paths.tsv') if r['cut']=='OE'},
                            changed={f:sha(p/f) for f in actual})
    for name in ('MMC558','loader'):
        rows=table(t/maps[name]/'epoch568.tsv')
        epoch={}
        for leg in ('input','sync'):
            paths=[r for r in rows if r['path']==leg]
            assert len({(r['corner'],int(r['bit'])) for r in paths})==96
            epoch[leg]=dict(worst_slack_ns=min(float(r['slack']) for r in paths),
                            max_data_delay_ns=max(float(r['data_delay']) for r in paths))
        boards[name]['epoch']=epoch
    phases = {}
    for name,folder in [('base',maps['571A']),('joint',maps['joint']),('revocable',maps['revocable'])]:
        checks = read(t/('nes-start572-func01-'+name)/'result.json')
        assert all(sha(t/folder/n)==v for n,v in checks['inputs'].items())
        assert checks['wiring']==sha(t/folder/'nes_live_joint.sv')
        phases[name] = checks
        assert checks['phases']==phases['base']['phases']
    # Isolated controls use exactly the loader/guard implementations exercised above.
    for f in ('nes_live_joint.sv','nes_diag_clock_guard127.sv','nes_rom_spi.sv'):
        control = 'loader' if f=='nes_rom_spi.sv' else 'memory'
        other = 'memory' if control=='loader' else 'loader'
        assert sha(t/maps[control]/f)==sha(t/maps['joint']/f)
        assert sha(t/maps[other]/f)==sha(base/f)
    pins={}
    for name,folder in [('joint','nes-start572-pins'),('revocable','nes-start572-pins-revocable')]:
        r=read(t/folder/'result.json')
        assert all(sha(t/maps[name]/f)==h for f,h in r['modules'].items())
        assert r['top']==sha(t/maps[name]/'fxpak_nes_screen137_top.sv')
        for f in ('results','latency_ps','mux_cases'):
            assert r[f]==prior['cases']['aperture_reset']['rtl'][f]
        pins[name]=r
    for i,phase in enumerate(prior['schedule'],1):
        d=t/f'nes-start572-replay{i}'
        assert read(d/'audit.json')==phase['audit']
        for f in ('arrivals.tsv','window.csv','bank561.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
            assert sha(d/f)==sha(t/f'nes-bus571-play{i}'/f),f
    a.out.write_text(json.dumps(dict(boards=boards,functional=phases,pins=pins,schedule=prior['schedule'],
        scope='Original Quartus constraints. Separate Questa RTL and Mesen 65816 replay with fixed ARM/SPI/IRQ/ROM arrivals. No new hardware run.'),indent=2)+'\n')


if __name__=='__main__':
    main()
