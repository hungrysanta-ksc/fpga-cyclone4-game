# SPDX-License-Identifier: MIT
"""Compare actual RTL tile/bank timing on one serial Questa seat."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def test(a):
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional/close561_tb.sv'
    a.out.mkdir(parents=True,exist_ok=False)
    results={}
    def run(tool,args,label):
        with (out/(label+'.log')).open('wb') as log:
            subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=out,stdout=log,stderr=subprocess.STDOUT,
                           timeout=60,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        return (out/(label+'.log')).read_text(errors='replace')
    for name,board in [('base',a.base),('early',a.board)]:
        out=a.out/name;out.mkdir()
        run('vlib',['work'],'lib')
        files=[board/('nes_'+s+'.sv') for s in ('domain_reset124','native_mailbox206','bulk_aperture188','bulk_control194','tile205','tile_bulk206')]
        run('vlog',['-sv',*(['+define+EARLY'] if name=='early' else []),*files,bench],'compile')
        for mode in (['normal','cancel','partial'] if name=='early' else ['normal','cancel']):
            for shifted in (False,True):
                label=f'{name}-{mode}-{int(shifted)}'
                log=run('vsim',['-c','-voptargs=+acc','close561_tb',*(['+SHIFT'] if shifted else []),
                               *([] if mode=='normal' else ['+'+mode.upper()]),'-do','run -all; quit -f'],label)
                assert 'PASS561 '+('STOP' if mode=='cancel' else mode.upper()) in log,label
                results[label]=re.findall(r'TRACE (\w+) (\d+(?: \d+)?)',log)
    (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','board','out','bin'):p.add_argument('--'+n,type=Path,required=True)
    test(p.parse_args())
