# SPDX-License-Identifier: MIT
"""Run epoch207 tests with the board's shared NES reset release contract.
Uses real reset124; RAM initialization/loader status are fixtures, not full board.
"""
from pathlib import Path
import argparse,json,os,subprocess
from nes_board204 import ROOT,BASE,sha,replace

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 src=ROOT/'tools/test_nes_epoch207.py';s=src.read_text()
 s=replace(s,"BASE/'probes/nes-board207/source01'","BASE/'probes/nes-board207/source02'")
 anchor=" s=s.replace('integer checks=0;'"
 before=''' s=replace(s,' nes_source_epoch207 dut(',''' + repr(' wire local_reset;\n nes_domain_reset124 board_core_release(.clk(nes_clk),.raw_reset(reset||!run),.reset(local_reset));\n nes_source_epoch207 dut(.local_reset(local_reset),') + ''')
'''
 s=replace(s,anchor,before+anchor)
 s="import sys\nsys.path.insert(0,"+repr(str(ROOT/'tools'))+")\n"+s
 f=a.out/'runner.py';f.write_text(s,encoding='utf8',newline='\n')
 with (a.out/'run.log').open('wb') as log:
  r=subprocess.run([os.sys.executable,'-B','-X','utf8',str(f),'--out',str(a.out/'sim'),'--questa-bin',str(a.questa_bin)],stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(a.out/'run.log').read_text(errors='replace')[-4000:]
 result=json.loads((a.out/'sim/result.json').read_bytes());assert result['passed']
 result['runner_sha256']=result.pop('script_sha256');result['script_sha256']=sha(Path(__file__))
 result['source_pins']['repository-nes-milestone/tools/test_nes_epoch207.py']=sha(src)
 result['scope']=__doc__
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print('PASS shared207 baseline20/cold32/negative')
if __name__=='__main__':main()
