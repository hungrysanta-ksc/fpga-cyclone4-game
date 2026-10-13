# SPDX-License-Identifier: MIT
"""Same-edge effects plus establishment of one-cycle counter-action invariant."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_counterpulse167 import transform
from test_nes_check165 import bench as prior_bench,REGS
from test_nes_commandpulse165 import connected as prior_connected

EXTRA='captured decoded_error approved_pulse offset_zero_command offset_length_command check_request_tag'.split()
def bench():
 s=prior_bench().replace('[10:0] f','[11:0] f').replace('f<2048','f<4096')
 s=s.replace(' dut.check_next=n;', '\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in EXTRA)+'\n dut.check_next=n;')
 s=s.replace('dut.pending=1;refdut.pending=1;', 'dut.pending=!f[11];refdut.pending=!f[11];')
 s=s.replace(' #1;mem_clk=1;#1;', '''
 dut.check_request_tag=n;refdut.check_request_tag=n;
 refdut.pending_counter_clear=(op==0||op==4||op==6) && !f[7] && !f[8];
 refdut.pending_counter_inc=op==8 && !f[7] && !f[8];
 dut.pending_counter_clear=refdut.pending && refdut.pending_counter_clear;
 dut.pending_counter_inc=refdut.pending && refdut.pending_counter_inc;
 #1;mem_clk=1;#1;''')
 return s.replace('PASS CHECK165','PASS COUNTERPULSE167')

def connected():
 s=prior_connected()
 # The selected loader stores one-hot phase; state is a read-only view.
 assert s.count('boot.loader.state=4;')==1
 s=s.replace('boot.loader.state=4;',"boot.loader.phase=16'h10;")
 needle='if($countones(dut.approved_pulse)>1)$fatal(1,"PULSE165 multiple approved commands");'
 assert s.count(needle)==1
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"COUNTERPULSE167 sequential {n}");' for n in REGS+EXTRA)
 compare+='\nif(dut.pending_counter_clear !== (refdut.pending && refdut.pending_counter_clear) || dut.pending_counter_inc !== (refdut.pending && refdut.pending_counter_inc))$fatal(1,"COUNTERPULSE167 pulse invariant");'
 s=s.replace(needle,compare)
 s=s.replace("dut.approved_pulse=6'b010000;", "dut.approved_pulse=6'b010000;refdut.approved_pulse=6'b010000;")
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 (a.out/'step_tb.sv').write_text(bench());(a.out/'connected_tb.sv').write_text(connected())
 def run(tool,args,label,expected=None):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if expected:assert expected in log and 'PASS TAG165' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','step_tb.sv','connected_tb.sv'],'compile')
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 steps=run('vsim',sim('check165_tb'),'steps');assert 'PASS COUNTERPULSE167 states=1048576' in steps
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 wrong=new.replace('pending_counter_clear<=0;pending_counter_inc<=0;\n   if(captured)', '/* wrong: stale actions */\n   if(captured)');assert wrong!=new
 (a.out/'wrong.sv').write_text(wrong);run('vlog',['-sv','wrong.sv'],'negative-compile');run('vsim',sim('tag165_tb'),'negative','COUNTERPULSE167 pulse invariant')
 result=dict(passed=True,conditional_steps=1048576,same_edge_effects=True,pulse_invariant=True,stale_pulse_rejected=True,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.candidate/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),sources={n:sha(a.out/n) for n in ['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','step_tb.sv','connected_tb.sv']},public_sources={n:sha(ROOT/n) for n in ['tools/nes_counterpulse167.py','tools/test_nes_counterpulse167.py','tools/test_nes_check165.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tests/nes-functional/tag165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['sources','public_sources']}))
if __name__=='__main__':main()
