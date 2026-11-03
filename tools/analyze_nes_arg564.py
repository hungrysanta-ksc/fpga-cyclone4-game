# SPDX-License-Identifier: MIT
"""Join the linked SPI differential and post-fit stage timing with the full board gate."""
import argparse
import csv
import json
from pathlib import Path
from analyze_nes_owner562 import board,read
from analyze_nes_guard563 import timing_inventory
from nes_raw506 import sha


def analyze(a):
    root=Path(__file__).resolve().parents[1]
    previous=read(root/'analysis/guard563-verification.json')
    control=read(root/'analysis/owner562-verification.json')['boards']['MMC558']
    spi=read(a.rtl/'result.json')
    assert sha(a.base/'output_files/board.sof')==previous['board']['SOF']
    assert spi['reference']==sha(a.base/'nes_rom_spi.sv') and spi['candidate']==sha(a.board/'nes_rom_spi.sv')
    assert spi['bench']==sha(root/'tests/nes-functional/arg564_tb.sv')
    pins=read(root/'analysis/trial558-verification.json')['inputs']
    assert [n for n in pins if sha(a.base/n)!=sha(a.board/n)]==['nes_rom_spi.sv']
    paths={}
    for name,folder in [('563',a.base),('564',a.board)]:
        with (folder/'arg564-paths.tsv').open() as f:
            paths[name]=list(csv.DictReader(f,delimiter='\t'))
    def cut(n,k):
        return [v for v in paths[n] if v['cut']==k]
    assert len(cut('563','old_capture'))==3 and min(float(v['slack']) for v in cut('563','old_capture'))<0
    assert not cut('564','old_capture') and not cut('563','decode') and not cut('563','write')
    for k in ('decode','write'):
        stages=cut('564',k)
        assert len(stages)==3 and all(float(v['slack'])>0 for v in stages)
    new=board(a.board)
    rows=new['rows'];base=control['rows']
    assert base.keys()==rows.keys()
    worse={k:[base[k],v] for k,v in rows.items() if v[0]<min(0,base[k][0])}
    regressed=[]
    for k in worse:
        corner,detail=k.split(' Model ')
        kind,clock=detail.split(" '");clock=clock[:-1]
        tag=('85c' if '85C' in corner else '0c')
        speed='slow' if corner.startswith('Slow') else 'fast'
        row,=[p for p in paths['564'] if p['cut']==('OE' if clock=='n/a' else clock)
              and p['check']==kind.lower() and speed in p['corner'] and tag in p['corner']]
        assert float(row['slack'])==rows[k][0]
        regressed.append(dict(summary=k,from_reg=row['from'],to=row['to'],loss_ns=round(base[k][0]-rows[k][0],3)))
    phases=[]
    for i,prior in enumerate(previous['phases'],1):
        trace=a.traces/f'nes-owner562-run{i}';audit=a.traces/f'nes-arg564-replay{i}'
        replay=read(audit/'audit.json')
        assert replay==prior['audit'] and sha(trace/'window.csv')==replay['trace']
        for g in range(905,958):assert sha(trace/f'frame-{g}.rgb')==sha(audit/f'frame-{g}.rgb')
        phases.append(dict(start=prior['start'],replay=replay,dense_VB=prior['dense_VB'],dense_ms=prior['dense_ms'],
                           final_ACK=prior['last_ACK'],waits=prior['waits'],wait957=prior['wait957']))
    capture=timing_inventory(a.board);fit=new['fit']
    local=all(fit[v+'_'+k+'_ns']>=0 for v in ('implementation','nominal') for k in ('setup','hold'))
    return dict(spi=spi,paths=paths,board=new,worse_than_MMC558=worse,regressed_endpoints=regressed,
                capture=capture,phases=phases,related_STA_pass=local,
                trial_gate=local and not worse and capture['mixed_corner_margin_ns']>0
                           and new['unconstrained']==control['unconstrained'])


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','board','rtl','traces','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n')
