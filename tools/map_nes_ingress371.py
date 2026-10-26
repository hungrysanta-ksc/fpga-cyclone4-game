# SPDX-License-Identifier: MIT
"""Whole Quartus Lite MAP with exactly the same five canonical replacements."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,sha
from nes_ingress371 import materialize,COMMON
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--rx-only',action='store_true');a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-source368/map01'
 for f in old.rglob('*'):
  rel=f.relative_to(old)
  if any(x in ('db','incremental_db','work','output_files') for x in rel.parts):continue
  if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
   target=d/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
 materialize(d)
 if a.rx_only:
  for n in ('nes_source_tile192.sv','nes_chr_cache192.sv','nes_plan_path267.sv'):shutil.copyfile(old/n,d/n)
 pins={f.relative_to(d).as_posix():sha(f) for f in d.rglob('*') if f.is_file()}
 with (d/'map.log').open('wb') as log:
  run=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 raw=(d/'map.log').read_text(errors='replace');bad=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
 result=dict(rx_only=a.rx_only,passed=run.returncode==0 and not bad,undriven=bad,actual_inputs=pins,shared_boundary={n:sha(d/n) for n in COMMON},FIT=False,STA=False)
 if (d/'output_files/board.map.summary').exists():result['summary']=(d/'output_files/board.map.summary').read_text()
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'];print(result['summary'])
if __name__=='__main__':main()
