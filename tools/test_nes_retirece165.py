# SPDX-License-Identifier: MIT
"""Compare counter enable/fault priority, live length capture and connected SPI."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_retirece165 import transform
from test_nes_predecode165 import bench as capture_bench
from test_nes_check165 import REGS

from test_nes_balancedlength165 import bench as capture_only,connected
from test_nes_check165 import bench as counter_only

def bench():
 s=capture_only();c=counter_only();a=c.index('task step(');b=c.index('initial begin',a)
 task=c[a:b]
 needle=" check_response_address=f[9]?(n^19'h40001):n;"
 assert task.count(needle)==1
 task=task.replace(needle,needle+"""
 dut.check_request_tag=n;refdut.check_request_tag=n;
 dut.pending_counter_clear=!f[7] && !f[8] && (op==0 || op==4 || op==6);
 refdut.pending_counter_clear=dut.pending_counter_clear;
 dut.pending_counter_inc=!f[7] && !f[8] && op==8;
 refdut.pending_counter_inc=dut.pending_counter_inc;
""")
 s=s.replace('integer captures=0;',task+'integer captures=0;',1)
 begin='initial begin\n'
 assert s.count(begin)==1
 loops=""" for(integer n=0;n<524288;n++)step(n,0,8,(&n[7:0]));
 for(integer f=0;f<2048;f++)for(integer op=0;op<16;op++)for(integer p=0;p<8;p++)
  step((19'h7ffff >> p),f,op,p[0]);
 $display("PASS RETIRECE165 states=%0d",count);
"""
 return s.replace(begin,begin+loops,1)

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
  if expected:assert expected in log and 'PASS STOPCLEAR165' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','capture_tb.sv','tag165_tb.sv'],'compile')
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',sim('check165_tb'),'capture');assert 'PASS STOPCLEAR165 captures=393741' in log and 'PASS RETIRECE165 states=786432' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 needle='&& !check_fault &&';assert new.count(needle)==1
 (a.out/'wrong-fault.sv').write_text(new.replace(needle,"&& 1'b1 &&"))
 run('vlog',['-sv','wrong-fault.sv'],'negative-compile');run('vsim',sim('check165_tb'),'negative','CHECK165 mismatch check_next')
 names=['tools/nes_retirece165.py','tools/nes_length165.py','tools/nes_lengthkeep165.py','tools/test_nes_retirece165.py','tools/test_nes_balancedlength165.py','tools/test_nes_stopclear165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py','tests/nes-functional/tag165_tb.sv']
 result=dict(passed=True,states=786432,captures=393741,retirement_live_length_changed=True,wrong_fault_gate_rejected=True,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
