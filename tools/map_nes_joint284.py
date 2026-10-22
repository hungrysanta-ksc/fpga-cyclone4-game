# SPDX-License-Identifier: MIT
"""Whole Lite MAP from pinned280 sources, shared progress/IRQ284 patch."""
import argparse,json,shutil,subprocess,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_joint284 import from280 as apply


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
    old=BASE/'probes/nes-joint280/board01'
    for f in old.rglob('*'):
        rel=f.relative_to(old)
        if any(v in ('db','incremental_db','output_files','work') for v in rel.parts):continue
        if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
            t=d/rel;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t)
    apply(d)
    pins={p.relative_to(d).as_posix():sha(p) for p in d.rglob('*') if p.is_file()}
    for n in ('nes_joint282.py','nes_joint283.py','nes_joint284.py','map_nes_joint284.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
    with (d/'map.log').open('wb') as log:
        r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    raw=(d/'map.log').read_text(errors='replace');bad=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
    result=dict(passed=r.returncode==0 and not bad,actual_inputs=pins,undriven=bad,FIT=False,STA=False)
    if (d/'output_files/board.map.summary').exists():result['summary']=(d/'output_files/board.map.summary').read_text()
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result if not result['passed'] else result['summary']))
    assert result['passed']


if __name__=='__main__':main()
