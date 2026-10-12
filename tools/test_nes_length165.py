# SPDX-License-Identifier: MIT
"""Loader same-edge equality flag: command states and every19-bit increment."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROOT,sha
from nes_predecode165 import loader

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.prepared/'nes_rom_loader.sv').read_text();assert new==loader(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #',1));(a.out/'candidate.sv').write_text(new)
 s=(ROOT/'tests/nes-functional/counter131_diff_tb.sv').read_text()
 s=s.replace('reg mem_clk=0,reset=1;','reg mem_clk=0,reset=1,commands_blocked=0;')
 for typ in ['nes_rom_loader dut','nes_rom_loader_reference refdut']:s=s.replace(typ+'(',typ+'(.commands_blocked(commands_blocked),')
 s=s.replace('for(integer mode=0;mode<2;mode++)','for(integer phase=0;phase<2;phase++)\n for(integer blocked=0;blocked<(phase==0?2:1);blocked++)\n for(integer mode=0;mode<(phase==0?2:1);mode++)')
 s=s.replace('state=0;state<9','state=(phase==0?0:8);state<9').replace('commands<64','commands<(phase==0?64:1)').replace('length_case<3','length_case<(phase==0?6:524288)').replace('failed<2','failed<(phase==0?2:1)').replace('rem_case<4','rem_case<(phase==0?4:1)')
 s=s.replace('length=length_case==0?0:(mode?98304:81920)-(length_case==1?1:0);',"length=phase==1?length_case:length_case==0?0:length_case==1?393215:length_case==2?393216:length_case==3?393217:length_case==4?524287:1234;")
 s=s.replace('{load_begin,load_valid,load_end,start,stop,load_chr32}=commands;','commands_blocked=blocked;\n        {load_begin,load_valid,load_end,start,stop,load_chr32}=commands;')
 s=s.replace('dut.fault=failed;',"dut.count_complete=(length==393216);\n        dut.fault=failed;",1)
 s=s.replace('(dut.state==2 || dut.state==3 || dut.state==7 || dut.state==8) && dut.remaining!==refdut.remaining','dut.remaining!==refdut.remaining')
 s=s.replace('checks++;','if(dut.count_complete !== (refdut.loaded_bytes==393216))$fatal(1,"LENGTH165 flag mismatch");\n        checks++;')
 s=s.replace('#1000000;','#20000000;')
 (a.out/'counter131_diff_tb.sv').write_text(s)
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert 'LENGTH165 flag mismatch' in log and 'PASS131' not in log
  else:assert r.returncode==0 and '** Fatal:' not in log and '** Error:' not in log,(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','counter131_diff_tb.sv'],'compile')
 args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',args,'equivalence');assert 'one_step_cases=628736' in log
 needle="count_complete<=loaded_bytes==total-1'b1;";assert new.count(needle)==1
 (a.out/'wrong-last.sv').write_text(new.replace(needle,'count_complete<=loaded_bytes==total;'))
 run('vlog',['-sv','wrong-last.sv'],'negative-compile');run('vsim',args,'negative',True)
 result=dict(passed=True,states=628736,command_states=104448,increment_values=524288,wrong_terminal_count_rejected=True,source_sha256=sha(a.prepared/'nes_rom_loader.sv'),reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_predecode165.py','tools/test_nes_length165.py','tests/nes-functional/counter131_diff_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
