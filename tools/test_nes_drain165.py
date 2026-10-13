# SPDX-License-Identifier: MIT
"""Loader transition, error precedence, pulse and pin equivalence with command inhibit."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROOT,sha
from nes_compare165 import drain

def bench():
    s=(ROOT/'tests/nes-functional/counter131_diff_tb.sv').read_text()
    s=s.replace('reg mem_clk=0,reset=1;','reg mem_clk=0,reset=1,commands_blocked=0;')
    for typ in ['nes_rom_loader dut','nes_rom_loader_reference refdut']:s=s.replace(typ+'(',typ+'(.commands_blocked(commands_blocked),')
    s=s.replace('for(integer mode=0;mode<2;mode++)','for(integer blocked=0;blocked<2;blocked++)\n  for(integer mode=0;mode<2;mode++)')
    s=s.replace('length_case<3','length_case<6').replace('rem_case<4','rem_case<128')
    s=s.replace('length_case==0?0:(mode?98304:81920)-(length_case==1?1:0)','length_case==0?0:length_case==1?393215:length_case==2?393216:length_case==3?393217:length_case==4?524287:1234')
    s=s.replace('remaining=rem_case==0?1:rem_case==1?2:rem_case==2?22:64;','remaining=rem_case;')
    s=s.replace('{load_begin,load_valid,load_end,start,stop,load_chr32}=commands;','commands_blocked=blocked;\n        {load_begin,load_valid,load_end,start,stop,load_chr32}=commands;')
    s=s.replace('dut.fault=failed;',"dut.count_complete=(length==393216);refdut.count_complete=(length==393216);\n        dut.fault=failed;",1)
    s=s.replace('(dut.state==2 || dut.state==3 || dut.state==7 || dut.state==8) && dut.remaining!==refdut.remaining','dut.remaining!==refdut.remaining')
    s=s.replace('checks++;','if(dut.count_complete !== refdut.count_complete)$fatal(1,"DRAIN165 count flag");\n        checks++;')
    return s.replace('#1000000;','#30000000;')

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.prepared/'nes_rom_loader.sv').read_text();assert new==drain(old)
    a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #',1));(a.out/'candidate.sv').write_text(new)
    (a.out/'counter131_diff_tb.sv').write_text(bench())
    def run(tool,args,label,negative=False):
        with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        log=(a.out/(label+'.log')).read_text(errors='replace')
        if negative:assert '** Fatal: DIFF131' in log and 'PASS131' not in log
        else:assert r.returncode==0 and '** Fatal:' not in log and '** Error:' not in log,(label,log[-2000:])
        return log
    run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','counter131_diff_tb.sv'],'compile')
    args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
    log=run('vsim',args,'equivalence');assert 'one_step_cases=3342336' in log
    needle='if(!stop && (commands_blocked || !(load_begin || load_end || start)))advance_phase();';assert new.count(needle)==1
    (a.out/'wrong-stop.sv').write_text(new.replace(needle,'if(commands_blocked || !(load_begin || load_end || start))advance_phase();'))
    run('vlog',['-sv','wrong-stop.sv'],'negative-compile');run('vsim',args,'negative',True)
    result=dict(passed=True,states=3342336,timer_values=128,wrong_stop_drain_rejected=True,source_sha256=sha(a.prepared/'nes_rom_loader.sv'),reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_compare165.py','tools/test_nes_drain165.py','tests/nes-functional/counter131_diff_tb.sv']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
