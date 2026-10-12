# SPDX-License-Identifier: MIT
"""Read-only routed STA using pinned155 clocks, retaining all stricter-target reports."""
from pathlib import Path
import argparse,json,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','fit','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.fit;e=a.baseline/'nes-game155/evidence'
 assert not (o/'nominal165-result.json').exists()
 pub=json.loads((ROOT/'analysis/game155-verification.json').read_bytes())
 assert sha(e/'manifest.json')==pub['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert sha(e/'asm/board.sdc')==pins['asm/board.sdc']
 nominal=(e/'asm/board.sdc').read_text()
 extra='\n'+(ROOT/'src/nes/diagnostics/nes_game156_budget.sdc').read_text()+(ROOT/'src/nes/diagnostics/nes_game160_budget.sdc').read_text()
 assert (o/'board.sdc').read_text().rstrip()==(nominal+extra).rstrip()
 before={f.relative_to(o).as_posix():sha(f) for f in o.rglob('*') if f.is_file() and
  (f.suffix in ['.sv','.v','.vhd','.qsf','.qpf','.sdc'] or ('db' in f.parts and not f.name.endswith('.taw.rdb') and '_io_sim_cache.' not in f.name))}
 (o/'nominal165.sdc').write_bytes((e/'asm/board.sdc').read_bytes())
 s=(ROOT/'tools/nes_secondary165_timing.tcl').read_text()
 s=s.replace('read_sdc\n','read_sdc nominal165.sdc\n',1).replace('secondary165','nominal165')
 (o/'nominal165.tcl').write_text(s)
 with (o/'nominal165.log').open('w') as f:
  subprocess.run([str(a.quartus_bin/'quartus_sta.exe'),'-t','nominal165.tcl'],cwd=o,stdout=f,stderr=subprocess.STDOUT,check=True)
 for n,h in before.items():assert sha(o/n)==h,n
 result=dict(nominal_sdc_sha256=sha(o/'nominal165.sdc'),implementation_sdc_sha256=sha(o/'board.sdc'),preserved=before,
  public_sources={n:sha(ROOT/n) for n in ['tools/check_nes_retire165_nominal.py','tools/nes_secondary165_timing.tcl']},
  scope='Exact pinned155 clocks only. Original stricter budgets and reports retained. No fit, clock-period, falsepath or multicycle change. Not IO/CDC signoff.')
 (o/'nominal165-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS unchanged routed inputs; nominal reports separate from implementation budgets')
if __name__=='__main__':main()
