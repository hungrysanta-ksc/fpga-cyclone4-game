# SPDX-License-Identifier: MIT
"""Compare clock-fault shutdown and requalification on the board's actual RTL."""
import argparse
import json
import re
import subprocess
from pathlib import Path


def run(a):
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional/guard563_tb.sv'
    a.out.mkdir(parents=True,exist_ok=False)
    result={}
    for name,board in [('original',a.base),('split',a.board)]:
        d=a.out/name;d.mkdir()
        def execute(tool,args,label):
            with (d/(label+'.log')).open('wb') as f:
                subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=d,stdout=f,stderr=subprocess.STDOUT,
                               timeout=90,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            return (d/(label+'.log')).read_text(errors='replace')
        execute('vlib',['work'],'lib')
        files=[board/('nes_'+n+'.sv') for n in ('domain_reset124','diag_clock_guard127','diag_startup_guard','rom_physical')]
        execute('vlog',['-sv',*(['+define+SPLIT'] if name=='split' else []),*files,bench],'compile')
        for phase in (0,1):
            log=execute('vsim',['-c','guard563_tb',*(['+SHIFT'] if phase else []),'-do','run -all; quit -f'],f'phase{phase}')
            assert 'PASS563 6 losses and common reset' in log,(name,phase)
            rows=[list(map(int,m)) for m in re.findall(r'LOSS563 (\d) (\d) (\d+)',log)]
            assert len(rows)==6
            result[f'{name}{phase}']=rows
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('base','board','bin','out'):p.add_argument('--'+name,required=True,type=Path)
    run(p.parse_args())
