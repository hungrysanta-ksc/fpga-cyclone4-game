"""Run the paired board bus/endpoint with actual SPI and SNES strobes."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_raw506 import sha

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    files=['nes_sink_bus165.sv','nes_sink_spi165.sv','nes_sink_bridge165.sv','nes_domain_reset124.sv','sink-program.hex']
    for f in files:shutil.copyfile(a.board/f,a.out/f)
    shutil.copyfile('tests/nes-functional/progress680_tb.sv',a.out/'progress680_tb.sv')
    commands=[('vlib',['work']),('vlog',['-sv',*files[:-1],'progress680_tb.sv'])]
    commands.extend((f'vsim{i}',['-c','progress680_tb',f'-gPHASE={phase}','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0']) for i,phase in enumerate((0,8)))
    for name,args in commands:
        tool='vsim' if name.startswith('vsim') else name
        with (a.out/(name+'.log')).open('wb') as log:
            subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
        if tool=='vsim':assert 'PASS680' in (a.out/(name+'.log')).read_text()
    result=dict(passed=True,phases=[0,8],pins={f:sha(a.out/f) for f in files+['progress680_tb.sv']},
        scope='Actual board host bridge; directed E1/event exact-edge injection and counter seed. No full board timing or CPU execution claim.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS680 RTL two phases')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('bin','board','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
