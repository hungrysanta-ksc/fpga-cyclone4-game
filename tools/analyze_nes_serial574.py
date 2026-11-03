# SPDX-License-Identifier: MIT
"""Bind serial identity tests to the routed board and unchanged display replay."""
import argparse,json,re
from pathlib import Path
from nes_raw506 import sha
from analyze_nes_owner562 import board,read
from analyze_nes_start572 import delta
from analyze_nes_reuse565 import table,pin_budget


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--traces',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();t=a.traces
    root=Path(__file__).resolve().parents[1]
    prior=read(root/'analysis/start572-verification.json')
    inputs=read(root/'analysis/trial558-verification.json')['inputs']
    base=t/'nes-start572-loader';candidate=t/'nes-serial574-board01'
    assert sorted(f for f in inputs if sha(candidate/f)!=sha(base/f))==['nes_source_epoch207.sv']
    for f in ('board.qsf','board.sdc','nominal204.sdc','cdc181.sdc'):
        assert sha(candidate/f)==sha(base/f)
    assert sha(candidate/'nes_source_epoch207.sv')==sha(root/'rtl/nes_source_epoch574.sv')
    boards={}
    for name,d in [('MMC558',t/'nes-admit556-board01'),('570',t/'nes-gate570-board05'),('572',base),('574',candidate)]:
        b=board(d)
        if name!='574':assert b['SOF']==prior['boards']['loader' if name=='572' else name]['SOF']
        boards[name]=b
    comparisons={k:delta(boards[k]['rows'],boards['574']['rows']) for k in ('MMC558','570','572')}
    result=read(t/'nes-serial574-test08/result.json')
    for f,h in result['modules'].items():assert sha(candidate/f)==h
    old=read(root/'analysis/epoch573-verification.json')
    assert result['phases']==[p['first'] for p in old['functional']['base']['phases']]
    logs=t/'nes-serial574-test08'
    counts=[]
    for phase in range(2):
        for name in ('transfer','skew'):
            log=(logs/f'{name}{phase}.log').read_text(errors='replace')
            m=re.search(r'PASS574 transfer=(\d+) edges=(\d+)\.\.(\d+)',log)
            assert m and m.groups()==('226','130','130')
            counts.append(dict(phase=phase,test=name,cases=226,transfer_NES_edges=130))
        text=(logs/f'capture{phase}.log').read_text(errors='replace')
        tiles=re.findall(r'TILE574 (\d+) first_request=(\d+) cache_epoch=(\w+)',text)
        assert tiles==[('0','16391','00c00000'),('1','16391','00c00000'),('2','16391','00c00003')]
    start=read(t/'nes-serial574-start01/result.json')
    pins=read(t/'nes-serial574-pins01/result.json')
    for f,h in start['inputs'].items():assert sha(candidate/f)==h
    for f,h in pins['modules'].items():assert sha(candidate/f)==h
    assert start['wiring']==sha(candidate/'nes_live_joint.sv')
    for key in ('latency_ps','results','mux_cases'):assert pins[key]==prior['pins']['joint'][key]
    for i,ph in enumerate(prior['schedule'],1):
        d=t/f'nes-serial574-replay{i}'
        assert read(d/'audit.json')==ph['audit']
        for f in ('arrivals.tsv','window.csv','bank561.csv',*(f'frame-{g}.rgb' for g in range(905,958))):
            assert sha(d/f)==sha(t/f'nes-epoch573-replay{i}'/f),f
    paths=table(candidate/'serial574-paths.tsv')
    assert len(paths)==42
    settled=[r for r in paths if not r['cut'].endswith('_first')]
    assert all(float(r['slack'])>0 for r in settled)
    assert len(comparisons['MMC558']['WNS'])==7
    fit=boards['574']['fit'];oldfit=boards['572']['fit']
    evidence=dict(boards=boards,comparisons=comparisons,functional=result,transfer=counts,start=start,pins=pins,
        fit_delta_572={k:fit[k]-oldfit[k] for k in ('LE','comb','FF','RAM_bits','M9K')},
        serial_paths=paths,start_paths=table(candidate/'start572.tsv'),PSRAM=pin_budget(candidate),
        schedule=prior['schedule'],selected='572 START only',trial_gate=False,
        sources={f:sha(candidate/f) for f in inputs},
        tests={p.name:sha(p) for p in logs.glob('*.log')},
        scope='Real RAM scrub, capture/ownership and source/cache/plan RTL. Earliest geometry lease and one-edge ROM response are fixtures. Separate actual 65816 replay of prior fixed ARM/SPI/IRQ/ROM arrivals. No new physical FPS, whole-game coexecution, analog CDC proof or menu hardware run.')
    a.out.write_text(json.dumps(evidence,indent=2)+'\n',newline='\n')


if __name__=='__main__':main()
