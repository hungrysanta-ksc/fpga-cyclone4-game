# SPDX-License-Identifier: MIT
"""One paired178 candidate: pinned177 inputs, raster admission and SNES ROM only."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_clip178 import raster,build

def prepare(prior,out):
    pins=json.loads((ROOT/'analysis/boundary177-verification.json').read_bytes())['verification']['sources']
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes())
    name='nes_native_raster_frame165.sv'
    (out/name).write_text(raster((prior/name).read_text()),encoding='utf8',newline='\n')
    client=build(out/'client178')
    (out/'sink-program.hex').write_bytes((out/'client178/sink-program.hex').read_bytes())
    r=dict(baseline=pins,sources={n:sha(out/n) for n in pins},changed=[name,'sink-program.hex'],client=client,
           public_sources={n:sha(ROOT/n) for n in ['tools/nes_clip178.py','tools/nes_clip178_fpga.py']},hardware_package=False)
    assert sum(r['sources'][n]!=pins[n] for n in pins)==2
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
