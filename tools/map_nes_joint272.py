# SPDX-License-Identifier: MIT
"""Matching whole-board Lite MAP; ordinary parser relocation from270."""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import BASE,ROOT,sha
from nes_joint272 import patch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--shared-context',action='store_true');a=p.parse_args()
    d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
    old=BASE/'probes/nes-joint270/board02';pins={}
    for f in old.rglob('*'):
        rel=f.relative_to(old)
        if any(x in ('work','db','incremental_db','output_files') for x in rel.parts):continue
        if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
            t=d/rel;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t);pins[rel.as_posix()]=sha(f)
    patch(d,shared=a.shared_context)
    p=d/'board.qsf';p.write_text(p.read_text()+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_parser272.sv\n',encoding='utf-8',newline='\n')
    for n in ['nes_joint272.py','map_nes_joint272.py']:shutil.copyfile(ROOT/'tools'/n,d/n)
    with (d/'map.log').open('wb') as f:
        r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    raw=(d/'map.log').read_text(errors='replace');undriven=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
    result=dict(passed=r.returncode==0 and not undriven,input_hashes=pins,
                script_sha256=sha(Path(__file__)),undriven_outputs=undriven,shared_context=a.shared_context,FIT=False,STA=False,scope=__doc__)
    if (d/'output_files/board.map.summary').exists():result['summary']=(d/'output_files/board.map.summary').read_text()
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False) if not result['passed'] else result['summary'])
    assert result['passed']


if __name__=='__main__':main()
