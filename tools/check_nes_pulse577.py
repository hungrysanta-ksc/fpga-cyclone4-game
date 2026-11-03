# SPDX-License-Identifier: MIT
"""Real loader timer: every timed edge, all command combinations, no state forcing."""
import argparse,json,re,subprocess
from pathlib import Path
from nes_raw506 import sha
p=argparse.ArgumentParser()
for k in ('board','out','bin'):p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
test=Path(__file__).resolve().parents[1]/'tests/nes-functional/pulse577_tb.sv'
def run(exe,args,name):
 with (a.out/(name+'.log')).open('wb') as f:
  subprocess.run([str(a.bin/(exe+'.exe')),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
 return (a.out/(name+'.log')).read_text(errors='replace')
run('vlib',['work'],'lib')
run('vlog',['-sv',a.board/'nes_rom_loader.sv',test],'compile')
result=[]
for phase in (0,1):
 log=run('vsim',['-c','pulse577_tb',*(['+SHIFT'] if phase else []),'-do','run -all; quit -f'],'phase'+str(phase))
 assert '** Fatal:' not in log and 'PASS577 cases=8320' in log,log[-1200:]
 line=next(s for s in log.splitlines() if 'PASS577' in s)
 result.append(dict(phase=phase,line=line))
(a.out/'result.json').write_text(json.dumps(dict(phases=result,loader=sha(a.board/'nes_rom_loader.sv'),test=sha(test)),indent=2)+'\n',newline='\n')
print(result)
