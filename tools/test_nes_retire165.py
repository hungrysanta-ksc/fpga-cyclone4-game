# SPDX-License-Identifier: MIT
"""All loader commands under common inhibit, preserving write drain and STOP."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROOT,sha
from nes_retire165 import loader

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.prepared/'nes_rom_loader.sv').read_text()
    assert new==loader(old);a.out.mkdir()
    (a.out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #',1))
    (a.out/'candidate.sv').write_text(new)
    bench=(ROOT/'tests/nes-functional/counter131_diff_tb.sv').read_text()
    bench=bench.replace('reg mem_clk=0,reset=1;','reg mem_clk=0,reset=1,commands_blocked=0;')
    bench=bench.replace('nes_rom_loader dut(','nes_rom_loader dut(.commands_blocked(commands_blocked),')
    start=bench.index('nes_rom_loader_reference refdut(');end=bench.index(';',start)
    ref=bench[start:end]
    for n in ['load_begin','load_valid','load_end','start']:ref=ref.replace(f'.{n}({n})',f'.{n}({n} && !commands_blocked)')
    bench=bench[:start]+ref+bench[end:]
    bench=bench.replace('for(integer mode=0;mode<2;mode++)','for(integer blocked=0;blocked<2;blocked++)\n  for(integer mode=0;mode<2;mode++)')
    assert bench.count('(mode?98304:81920)')==1
    bench=bench.replace('(mode?98304:81920)','393216')
    bench=bench.replace('{load_begin,load_valid,load_end,start,stop,load_chr32}=commands;','commands_blocked=blocked;\n        {load_begin,load_valid,load_end,start,stop,load_chr32}=commands;')
    # Both compared implementations now use exactly the same inactive preload.
    bench=bench.replace('(dut.state==2 || dut.state==3 || dut.state==7 || dut.state==8) && dut.remaining!==refdut.remaining','dut.remaining!==refdut.remaining')
    bench=bench.replace('#1000000;','#2000000;')
    (a.out/'counter131_diff_tb.sv').write_text(bench)
    def run(tool,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if negative:assert '** Fatal: DIFF131' in log and 'PASS131' not in log
        else:assert r.returncode==0 and '** Fatal:' not in log and '** Error:' not in log,(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','counter131_diff_tb.sv'],'compile')
    args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    assert 'PASS131 DIFF one_step_cases=52224' in run('vsim',args,'equivalence')
    needle='wire command_conflict=!commands_blocked && (';assert new.count(needle)==1
    (a.out/'wrong-inhibit.sv').write_text(new.replace(needle,'wire command_conflict=('))
    run('vlog',['-sv','wrong-inhibit.sv'],'negative-compile');run('vsim',args,'negative',True)
    result=dict(passed=True,states=52224,total_bytes=393216,inhibit_values=2,wrong_inhibit_rejected=True,
        reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),source_sha256=sha(a.prepared/'nes_rom_loader.sv'),
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_retire165.py','tools/test_nes_retire165.py','tests/nes-functional/counter131_diff_tb.sv']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
