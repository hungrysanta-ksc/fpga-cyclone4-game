# SPDX-License-Identifier: MIT
"""Latency-aware transaction comparison and cancellation at both queued stages."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_commandpulse165 import transform as pulse
from nes_update165 import spi
from test_nes_commandpulse165 import bench as prior_bench,connected as prior_connected
def transform(s):return spi(pulse(s))
def bench():
 s=prior_bench()
 s=s.replace("dut.command='0;", "dut.command='0;dut.offset_zero_command=0;dut.offset_length_command=0;")
 s=s.replace('dut.command=cmd;', "dut.command=cmd;dut.offset_zero_command=(cmd==8'h60);dut.offset_length_command=(cmd>=8'h61 && cmd<=8'h64);")
 return s
def connected():
 s=prior_connected()
 marker='if($countones(dut.approved_pulse)>1)'
 assert s.count(marker)==1
 s=s.replace(marker, "if(dut.offset_zero_command!==(dut.command==8'h60) || dut.offset_length_command!==((dut.command>=8'h61)&&(dut.command<=8'h64)))$fatal(1,\"UPDATE165 command-kind invariant\");\n  if(boot.loader.terminal!==(boot.loader.remaining==1))$fatal(1,\"UPDATE165 connected terminal\");\n  "+marker)
 return s
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.prepared/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.prepared/n).read_bytes())
 (a.out/'capture_tb.sv').write_text(bench());(a.out/'tag165_tb.sv').write_text(connected())
 def run(tool,args,label,expected=None):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if expected:assert expected in log and 'PASS COMMANDSTAGE165' not in log,(label,log[-2500:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2500:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','capture_tb.sv','tag165_tb.sv'],'compile')
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',sim('check165_tb'),'capture');assert 'PASS COMMANDSTAGE165 captures=393741 boundaries=120' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 for label,needle,replacement,expected in [
  ('overlap','(captured || pending) && !ss_sync[1]','pending && !ss_sync[1]','STAGE165 cancelled command escaped'),
  ('fault','wire command_retire_ok=!fault && ss_sync[1] && !check_fault &&','wire command_retire_ok=!fault && ss_sync[1] &&','PULSE165 same-edge cancellation'),
  ('header',"approved_pulse[0]<=pending_header_error==0 && pending_causes==0 &&", "approved_pulse[0]<=",'STAGE165 result load_begin')]:
  assert new.count(needle)==1
  (a.out/('wrong-'+label+'.sv')).write_text(new.replace(needle,replacement))
  run('vlog',['-sv','wrong-'+label+'.sv'],label+'-negative-compile');run('vsim',sim('check165_tb'),label+'-negative',expected)
 needle="offset_zero_command<=incoming==8'h60";assert new.count(needle)==1
 (a.out/'wrong-kind.sv').write_text(new.replace(needle,"offset_zero_command<=incoming==8'h61"))
 run('vlog',['-sv','wrong-kind.sv'],'kind-negative-compile')
 run('vsim',sim('tag165_tb'),'kind-negative','UPDATE165 command-kind invariant')
 names=['tools/nes_update165.py','tools/test_nes_update165.py','tools/nes_commandpulse165.py','tools/test_nes_commandpulse165.py','tools/nes_commandpayload165.py','tools/test_nes_commandpayload165.py','tools/nes_commandstage165.py','tools/test_nes_commandstage165.py','tools/test_nes_balancedlength165.py','tools/test_nes_stopclear165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py','tests/nes-functional/tag165_tb.sv']
 result=dict(passed=True,captures=393741,boundaries=120,added_mem_cycles=1,transaction_result_comparison=True,same_edge_equivalence=False,wrong_overlap_rejected=True,wrong_live_fault_rejected=True,wrong_header_rejected=True,same_edge_cancellation_checked=True,command_kind_invariant_checked=True,connected_terminal_checked=True,wrong_kind_rejected=True,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
