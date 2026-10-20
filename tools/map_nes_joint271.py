# SPDX-License-Identifier: MIT
"""Same complete270 board, replacing only the common E1 status engine."""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import BASE,ROOT,sha

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 old=BASE/'probes/nes-joint270/board02';pins={}
 for f in old.rglob('*'):
  rel=f.relative_to(old)
  if any(x in ('work','db','incremental_db','output_files') for x in rel.parts):continue
  if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
   target=d/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target);pins[rel.as_posix()]=sha(f)
 (d/'nes_spi270.sv').write_bytes((ROOT/'tools/nes_spi271.sv').read_bytes())
 for n in ['nes_spi271.sv','map_nes_joint271.py']:shutil.copyfile(ROOT/'tools'/n,d/n)
 with (d/'map.log').open('wb') as log:
  result=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 raw=(d/'map.log').read_text(errors='replace');undriven=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
 r=dict(passed=result.returncode==0 and not undriven,summary=(d/'output_files/board.map.summary').read_text(),
  input_hashes=pins,script_sha256=sha(Path(__file__)),SPI_sha256=sha(d/'nes_spi270.sv'),undriven_outputs=undriven,FIT=False,STA=False,scope=__doc__)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r['summary']);assert r['passed']

if __name__=='__main__':main()
