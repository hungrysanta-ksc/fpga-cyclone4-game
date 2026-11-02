# SPDX-License-Identifier: MIT
"""Run the pinned SPI receivers in lockstep on a single Questa Starter seat."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from nes_raw506 import once,sha


def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    old=a.base/'nes_rom_spi.sv';new=a.board/'nes_rom_spi.sv'
    ref=a.out/'ref_spi563.sv'
    ref.write_text(once(old.read_text(),'module nes_rom_spi_check(','module ref_spi563('),newline='\n')
    def execute(tool,args,name):
        log=a.out/(name+'.log')
        with log.open('wb') as f:
            subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,
                           timeout=120,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        return log.read_text(errors='replace')
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional/arg564_tb.sv'
    execute('vlib',['work'],'lib')
    execute('vlog',['-sv',ref,new,bench],'compile')
    phases=[]
    for i in range(2):
        log=execute('vsim',['-c','arg564_tb',*(['+SHIFT'] if i else []),'-do','run -all; quit -f'],f'phase{i}')
        match=re.search(r'PASS564 writes=266 trunc=56 armed=1 checks=(\d+)',log)
        assert match and int(match[1])>100000,(a.out,i)
        phases.append(int(match[1]))
    (a.out/'result.json').write_text(json.dumps(dict(reference=sha(old),candidate=sha(new),bench=sha(bench),
        writes=266,truncated=56,checks=phases),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('base','board','out','bin'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
