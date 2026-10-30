# SPDX-License-Identifier: MIT
"""Overlay only two502 capture files on the exact493 whole-board inputs."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 pins=json.loads((ROOT/'analysis/boot493-verification.json').read_text())['FPGA']['source_inputs']
 for n,h in pins.items():
  assert sha(a.baseline/n)==h,n
  q=a.out/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,q)
 for n in ['nes_native_planes165.sv','nes_native_frame201.sv']:shutil.copy2(ROOT/'src/fpga/nes_capture502'/n,a.out/n)
 (a.out/'board.qpf').write_text('QUARTUS_VERSION = "25.1"\nPROJECT_REVISION = "board"\n')
 new={n:sha(a.out/n) for n in pins}
 result=dict(baseline_inputs=pins,board_inputs=new,changed=[n for n in pins if pins[n]!=new[n]],scope=__doc__)
 assert set(result['changed'])=={'nes_native_planes165.sv','nes_native_frame201.sv'}
 (a.out/'source-pins.json').write_text(json.dumps(result,indent=2)+'\n')
 print(result['changed'])
