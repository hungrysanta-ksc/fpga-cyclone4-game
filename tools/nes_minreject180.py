# SPDX-License-Identifier: MIT
"""Reduce observer to three state bits; version3 marks reduced visibility."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_reject180 import replace
CHANGED=['nes_reject_witness180.sv','nes_ppu_history157.sv']

def prepare(prior,out):
    pins=json.loads((ROOT/'analysis/reject180-verification.json').read_bytes())['verification']['sources']
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes())
    n='nes_reject_witness180.sv';(out/n).write_bytes((ROOT/'src/nes/diagnostics/nes_minreject180.sv').read_bytes())
    n='nes_ppu_history157.sv';p=out/n;p.write_text(replace(p.read_text(),"8'd1,8'd96,8'd2","8'd1,8'd96,8'd3"),encoding='utf8',newline='\n')
    r=dict(baseline=pins,sources={n:sha(out/n) for n in pins},changed=CHANGED,
      public_sources={n:sha(ROOT/n) for n in ['tools/nes_minreject180.py','src/nes/diagnostics/nes_minreject180.sv']},history_schema=3,hardware_package=False)
    assert sorted(n for n in pins if r['sources'][n]!=pins[n])==sorted(CHANGED)
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
