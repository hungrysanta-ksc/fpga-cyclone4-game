# SPDX-License-Identifier: MIT
"""Separate the extra5.5ns and targeted5.3ns placement targets from unchanged real clock periods."""
from pathlib import Path
import argparse,json,sys
import check_nes_game150_timing as original
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','fit','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-game155/evidence';o=a.fit
 m=json.loads((ROOT/'analysis/game155-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];assert sha(e/'asm/board.sdc')==pins['asm/board.sdc']
 nominal=(e/'asm/board.sdc').read_text();budget=(ROOT/'src/nes/diagnostics/nes_game156_budget.sdc').read_text()
 assert (o/'board.sdc').read_text().rstrip()==(nominal+'\n'+budget+(ROOT/'src/nes/diagnostics/nes_game160_budget.sdc').read_text()).rstrip()
 prior=json.loads((o/'timing150-phase.json').read_bytes());assert not (o/'timing156-budget.json').exists()
 # Preserve the failed stricter target, never relabel it as having passed.
 (o/'timing150-phase.json').rename(o/'timing156-budget.json')
 for n in ['timing150.log','same-clock150.tsv','io150.tsv']:(o/n).rename(o/('budget156-'+n))
 (o/'nominal156.sdc').write_bytes((e/'asm/board.sdc').read_bytes())
 before={f.relative_to(o).as_posix():sha(f) for f in o.rglob('*') if f.is_file() and
  (f.suffix in ['.sv','.v','.vhd','.qsf','.qpf','.sdc'] or ('db' in f.parts and not f.name.endswith('.taw.rdb') and '_io_sim_cache.' not in f.name))}
 (o/'nominal156-inputs.json').write_text(json.dumps(before,indent=2)+'\n')
 original.TCL=original.TCL.replace('read_sdc\n','read_sdc nominal156.sdc\n',1)
 sys.argv=[sys.argv[0],'--fit',str(o),'--quartus-bin',str(a.quartus_bin)]
 original.main()
 for n,h in before.items():assert sha(o/n)==h,n
 result=json.loads((o/'timing150-phase.json').read_bytes())
 result.update(implementation_budget_setup_ns=prior['same_clock_setup_ns'],implementation_budget_passed=prior['passed'],
  nominal_sdc_sha256=sha(o/'nominal156.sdc'),routed_files_preserved=len(before),new_fit=False,
  nominal_contract='Exact155 clock SDC; no period/falsepath/multicycle change. Extra1565.5ns target is only placement guidance; its miss remains separate.')
 (o/'timing150-phase.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS156 unchanged clock contract; stricter placement target retained separately')
if __name__=='__main__':main()
