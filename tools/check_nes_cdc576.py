# SPDX-License-Identifier: MIT
"""Actual SPI73 diagnostic and shared host reset, including stopped clocks."""
import argparse,json,subprocess
from pathlib import Path
from nes_raw506 import once,sha
p=argparse.ArgumentParser()
for k in ('board','out','bin','reference'):p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parents[1]
(a.out/'sink-program.hex').write_bytes((a.board/'sink-program.hex').read_bytes())
top=(a.board/'fxpak_nes_screen137_top.sv').read_text()
block=top[top.index('wire host_cancel_reset;'):top.index(' nes_sink_bridge165 sink(')]
bench=once((root/'tests/nes-functional/cdc576_tb.sv').read_text(),'@FAULT_BLOCK@',block)
(a.out/'test.sv').write_text(bench,newline='\n')
files=[a.board/f for f in ['nes_domain_reset124.sv','nes_screen_status151.sv','nes_sink_bridge165.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_game_pad150.sv']]
reference=a.reference/'nes_sink_bridge165.sv'
(a.out/'reference.sv').write_text(once(reference.read_text(),'module nes_sink_bridge165(','module nes_sink_bridge165_ref('),newline='\n')
files.append(a.out/'reference.sv')
def run(tool,args,name):
    with (a.out/(name+'.log')).open('wb') as log:
        subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=a.out,check=True,timeout=120,stdout=log,stderr=subprocess.STDOUT)
    return (a.out/(name+'.log')).read_text(errors='replace')
run('vlib',['work'],'lib');run('vlog',['-sv',*files,a.out/'test.sv'],'compile')
results=[]
for phase in (0,1):
    log=run('vsim',['-c','cdc576_tb',*(['+SHIFT'] if phase else []),'-do','run -all; quit -f'],'phase'+str(phase))
    assert 'PASS576 captures=32' in log and '** Fatal:' not in log,log[-1000:]
    results.append(dict(phase=phase,line=next(x for x in log.splitlines() if 'PASS576' in x)))
(a.out/'result.json').write_text(json.dumps(dict(results=results,sources={f.name:sha(f) for f in files},top=sha(a.board/'fxpak_nes_screen137_top.sv')),indent=2)+'\n',newline='\n')
print(json.dumps(results))
