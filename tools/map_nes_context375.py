# SPDX-License-Identifier: MIT
"""One whole Lite MAP of the selected no-query6 capture specialization."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from nes_context375 import COMMON,board

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 reference=BASE/'probes/nes-source368/map01'
 for f in reference.rglob('*'):
  rel=f.relative_to(reference)
  if any(x in ('db','incremental_db','work','output_files') for x in rel.parts):continue
  if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
   dest=d/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
 board(d);pins={p.relative_to(d).as_posix():sha(p) for p in d.rglob('*') if p.is_file()}
 with (d/'map.log').open('wb') as log:
  r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 raw=(d/'map.log').read_text(errors='replace');bad=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
 result=dict(passed=r.returncode==0 and not bad,actual_inputs=pins,undriven=bad,shared_boundary={n:sha(d/n) for n in COMMON},FIT=False,STA=False)
 if (d/'output_files/board.map.summary').exists():result['summary']=(d/'output_files/board.map.summary').read_text()
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='actual_inputs'},indent=2));assert result['passed']
if __name__=='__main__':main()
