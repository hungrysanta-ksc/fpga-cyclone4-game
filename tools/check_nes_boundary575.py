# SPDX-License-Identifier: MIT
"""Check the held-word ownership/window used in the timing audit."""
import argparse,json,re,subprocess
from pathlib import Path
from nes_raw506 import sha

def main():
    p=argparse.ArgumentParser()
    for k in ('board','out','bin'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    bench=Path(__file__).resolve().parents[1]/'tests/nes-functional/boundary575_tb.sv'
    def run(tool,args,label,marker=None):
        log=a.out/(label+'.log')
        with log.open('wb') as f:subprocess.run([str(a.bin/(tool+'.exe')),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
        s=log.read_text(errors='replace')
        if marker:assert marker in s and '** Fatal:' not in s,s[-1200:]
        return s
    run('vlib',['work'],'lib')
    run('vlog',['-sv','-y',a.board,'+libext+.sv',a.board/'nes_native_mailbox206.sv',a.board/'nes_rom_physical.sv',bench],'compile')
    phases=[]
    for i in range(2):
        s=run('vsim',['-c','boundary575_tb',*(['+SHIFT'] if i else []),'-do','run -all;quit -f'],'phase'+str(i),'PASS575 HELD128 ROM64 RESET32')
        rows=re.findall(r'HELD575 capture=(\d+) width=(\d+) accepted=(\d+) checks=(\d+) min_ps=(\d+) budget_ps=(\d+)',s)
        assert len(rows)==2
        rom=re.findall(r'ROM575 reads=(\d+) checks=(\d+) min_ps=(\d+) budget_ps=(\d+)',s)
        assert len(rom)==1 and rom[0][0]=='64'
        assert 'RESET575 commands=32 fault_clear_edges=' in s
        phases.append(dict(mailbox=rows,ROM=rom,reset_commands=32))
    (a.out/'result.json').write_text(json.dumps(dict(phases=phases,RTL={n:sha(a.board/n) for n in ('nes_native_mailbox206.sv','nes_rom_physical.sv','nes_rom_boot.sv','nes_rom_loader.sv')},test=sha(bench)),indent=2)+'\n')

if __name__=='__main__':main()
