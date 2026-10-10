# SPDX-License-Identifier: MIT
"""Fresh physical-shell fit; no inherited virtual-pin timing signoff."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_board134 import prepare
from nes_cdc125_sta import put

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists()
 prepare(a.baseline,o);shutil.copy2(__file__,o/'executed-fit134.py')
 shutil.copy2(Path(__file__).with_name('nes_board134.py'),o/'executed-board134.py')
 m=dict(phases={},installable=False)
 for phase in ['map','fit','sta']:
  with (o/(phase+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'board'],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  m['phases'][phase]=r.returncode;put(o/'fit134.json',json.dumps(m,indent=2)+'\n')
  assert r.returncode==0,phase
  print(phase+' complete',flush=True)
 print((o/'output_files/board.fit.summary').read_text(errors='replace'))
 print((o/'output_files/board.sta.summary').read_text(errors='replace'))
if __name__=='__main__':main()
