# SPDX-License-Identifier: MIT
"""Exercise the selected collector/lease, real scrubs, STOP and the full Gray word."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from nes_raw506 import once,sha


def main():
    p=argparse.ArgumentParser()
    for name in ('base','board','bin','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    d=a.out
    d.mkdir(parents=True,exist_ok=False)
    tests=Path(__file__).resolve().parents[1]/'tests/nes-functional'
    ref=a.base/'nes_source_epoch207.sv'
    (d/'reference.sv').write_text(once(ref.read_text(),'module nes_source_epoch207(','module epoch572('))
    def run(tool,args,label,marker=None):
        log=d/(label+'.log')
        with log.open('wb') as f:
            subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=d,stdout=f,stderr=subprocess.STDOUT,
                           check=True,timeout=180)
        s=log.read_text(errors='replace')
        if marker and (marker not in s or '** Fatal:' in s):
            raise AssertionError((label,s[-650:]))
        return s
    run('vlib',['work'],'lib')
    compile_log=run('vlog',['-sv','-y',a.board,'+libext+.sv',d/'reference.sv',tests/'epoch573_tb.sv',
                            tests/'epoch568_tb.sv'],'compile')
    def sim(top,i,marker):
        return run('vsim',['-c',top,*(['+SHIFT'] if i else []),'-do','run -all; quit -f'],top+str(i),marker)
    sim('epoch568_tb',0,'PASS568 epoch=64')
    phases=[]
    for i in (0,1):
        s=sim('epoch573_tb',i,'PASS573 comparisons=')
        starts=re.findall(r'FIRST573 (\d+) (\w+) (\d+) (\d+) (\d+) (\d+)',s)
        assert len(starts)==3 and all(int(row[-1])>int(row[-3]) for row in starts)
        phases.append(dict(first=starts,comparisons=int(re.search(r'PASS573 comparisons=(\d+)',s)[1])))
    modules={f.name:sha(f) for f in a.board.glob('nes_*.sv') if re.search(r'Compiling module '+f.stem+r'\b',compile_log)}
    assert {'nes_source_epoch207.sv','nes_capture_lease201.sv','nes_native_capture201.sv','nes_local_memory.sv'}<=modules.keys()
    rejected=False
    source=(a.board/'nes_source_epoch207.sv').read_text()
    if 'assign live_epoch=visible_epoch;' in source:
        (d/'mutant.sv').write_text(once(source,'assign live_epoch=visible_epoch;',
                                       "assign live_epoch=cold_reset?32'd0:epoch_sync;"))
        run('vlog',['-sv',d/'mutant.sv'],'mutant-build')
        # Check the negative outcome explicitly. A tool failure or timeout does not count.
        log=run('vsim',['-c','epoch573_tb','-do','onbreak {quit -f}; run -all; quit -f'],'mutant')
        rejected='** Fatal: epoch visibility reset=0 ready=0 ref=00000000 actual=00c00000' in log
        assert rejected,log[-650:]
    (d/'result.json').write_text(json.dumps(dict(reference=sha(ref),modules=modules,phases=phases,
        carry_cases=64,exhaustion=True,missing_second_edge_rejected=rejected),indent=2)+'\n')


if __name__=='__main__':
    main()
