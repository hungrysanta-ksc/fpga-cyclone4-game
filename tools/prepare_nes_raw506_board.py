# SPDX-License-Identifier: MIT
"""Clone the pinned502 whole-board boundary; replace only the506 exporter."""
import argparse,json,shutil
from pathlib import Path
from check_nes_game478 import sha
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['baseline','candidate','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();pins=json.loads((ROOT/'analysis/capture502-verification.json').read_text())['FPGA']['whole_board_inputs']
    assert not a.out.exists();a.out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(a.baseline/n)==h,n
        d=a.out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,d)
    shutil.copy2(a.candidate/'nes_native_export203.sv',a.out/'nes_native_export203.sv')
    shutil.copy2(a.baseline/'nominal204.sdc',a.out/'nominal204.sdc')
    (a.out/'board.qpf').write_text('QUARTUS_VERSION = "25.1"\nPROJECT_REVISION = "board"\n')
    new={n:sha(a.out/n)for n in pins};changed=[n for n in pins if pins[n]!=new[n]]
    assert changed==['nes_native_export203.sv']
    (a.out/'source-pins.json').write_text(json.dumps(dict(baseline_inputs=pins,board_inputs=new,changed=changed,timing_support={'nominal204.sdc':sha(a.out/'nominal204.sdc')}),indent=2)+'\n')
    print(json.dumps(dict(changed=changed,input_files=len(pins))))
