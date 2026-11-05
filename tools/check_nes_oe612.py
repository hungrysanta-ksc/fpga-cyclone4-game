"""Cycle-exact physical reader comparison, including stopped-clock cancellation."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_raw506 import once,sha
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','board','out','bin'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    shutil.copy(a.board/'nes_rom_physical.sv',a.out)
    (a.out/'reference.sv').write_text(once((a.base/'nes_rom_physical.sv').read_text(),'module nes_rom_physical #','module nes_rom_physical_ref #'),newline='\n')
    shutil.copy(ROOT/'tools/nes_oe612_tb.sv',a.out)
    for tool,args in [('vlib',['work']),('vlog',['-sv','nes_rom_physical.sv','reference.sv','nes_oe612_tb.sv']),
                      ('vsim',['-c','nes_oe612_tb','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'])]:
        with (a.out/(tool+'.log')).open('wb') as f:subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
    lines=[x for x in (a.out/'vsim.log').read_text().splitlines() if 'PASS612' in x];assert len(lines)==5
    (a.out/'result.json').write_text(json.dumps(dict(lines=lines,reference=sha(a.base/'nes_rom_physical.sv'),candidate=sha(a.board/'nes_rom_physical.sv'),
         bench=sha(ROOT/'tools/nes_oe612_tb.sv'),log=sha(a.out/'vsim.log')),indent=2)+'\n',newline='\n')
