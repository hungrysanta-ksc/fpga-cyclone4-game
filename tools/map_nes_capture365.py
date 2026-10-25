# SPDX-License-Identifier: MIT
"""One whole Lite MAP of the repaired shared capture/source/plan boundary."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha
from nes_capture365 import REFERENCE,COMMON,board

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--early-release',action='store_true');a=p.parse_args()
    d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
    for f in REFERENCE.rglob('*'):
        rel=f.relative_to(REFERENCE)
        if any(v in ('db','incremental_db','output_files','work') for v in rel.parts):continue
        if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
            t=d/rel;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t)
    board(d,early=a.early_release)
    pins={p.relative_to(d).as_posix():sha(p) for p in d.rglob('*') if p.is_file()}
    for n in ('nes_capture365.py','map_nes_capture365.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
    with (d/'map.log').open('wb') as log:
        r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    raw=(d/'map.log').read_text(errors='replace');bad=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
    result=dict(passed=r.returncode==0 and not bad,actual_inputs=pins,undriven=bad,
                shared_boundary={n:sha(d/n) for n in COMMON},FIT=False,STA=False)
    if (d/'output_files/board.map.summary').exists():result['summary']=(d/'output_files/board.map.summary').read_text()
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='actual_inputs'},indent=2));assert result['passed']

if __name__=='__main__':main()
