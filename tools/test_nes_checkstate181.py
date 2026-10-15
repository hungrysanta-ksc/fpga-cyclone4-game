# SPDX-License-Identifier: MIT
"""Same-edge differential CHECK state and real SPI/reader transactions."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_checkstate181 import transform
from test_nes_check165 import REGS
from test_nes_counterpulse167 import EXTRA
from test_nes_rawstage167 import connected as old_connected

STATE=list(dict.fromkeys(REGS+EXTRA+'''sampled raw_causes raw_select raw_loaded raw_run raw_ready raw_load_ready
pending_counter_clear pending_counter_inc commit_clear commit_inc'''.split()))

def bench():
 inputs='mem_clk reset SPI_SS SPI_SCK SPI_MOSI load_ready loaded run_enable boot_fault boot_error loaded_bytes check_ready check_response check_fault check_response_address check_data'.split()
 ports=','.join('.'+n+'('+n+')' for n in inputs)
 seed='\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in STATE)
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"STATE181 mismatch {n} f=%h op=%h",f,op);' for n in STATE)
 setup={'check_enable':'f[3]','check_busy':'f[4]','check_done':'f[5]','verified':'f[6]',
 'fault':'f[7]','pending':'f[8]','sampled':'f[9]','captured':'f[10]',
 'ss_sync':'f[11]?0:3','decoded_error':'f[12]?4\'d8:0','commit_clear':'f[13]',
 'commit_inc':'f[14]','check_request_tag':"19'h12345",'check_next':"19'h12345",
 'pending_command':'op','pending_arg':"8'h96",'pending_causes':'f[12]?16:0',
 'approved_pulse':"op==3?6'b001000:op==4?6'b010000:0",'ss_previous':'1',
 'checked_data':"8'h35",'error_code':'f[7]?7:0'}
 assign='\n'.join(f'dut.{n}={v};refdut.{n}={v};' for n,v in setup.items())
 return '''`timescale 1ns/1ps
module state181_tb;
reg mem_clk=0,reset=0,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
reg load_ready=1,loaded=1,run_enable=0,boot_fault=0;
reg [3:0] boot_error=0;reg [18:0] loaded_bytes=19'h60000;
reg check_ready=1,check_response=0,check_fault=0;
reg [18:0] check_response_address=0;reg [7:0] check_data=8'ha6;
nes_rom_spi_check dut('''+ports+''');
baseline_check165 refdut('''+ports+''');
integer count=0,followups=0;
task step(input [15:0] f,input [3:0] op,input integer cycles);
begin
'''+seed+'\n'+assign+'''
 reset=f[15];check_fault=f[0];boot_fault=f[1];check_response=f[2];
 check_response_address=f[14]?19'h12344:19'h12345;
 repeat(cycles)begin
 #1;mem_clk=1;#1;
'''+compare+'''
 mem_clk=0;#1;count++;
 end
end endtask
initial begin
 for(integer f=0;f<65536;f++)for(integer op=0;op<16;op++)step(f,op,1);
 for(integer f=0;f<1024;f++)begin step((f*40503)^16'ha53c,f%16,8);followups++;end
 $display("PASS STATE181 edges=%0d followups=%0d",count,followups);$finish;
end
endmodule
'''

def connected():
 s=old_connected()
 # Prior harness seeded STOP for a decoder with different pipeline depth.
 # Both current modules have the identical pipeline; compare every register.
 anchor='// Explicitly shifted command acceptance; wire comparison below.'
 assert anchor in s
 cmp='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"STATE181 sequential {n}");' for n in STATE)
 return s.replace(anchor,cmp)

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 (a.out/'state_tb.sv').write_text(bench());(a.out/'connected_tb.sv').write_text(connected())
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert 'STATE181 mismatch' in log and 'PASS STATE181' not in log,(label,log[-3000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-3000:])
  return log
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv'],'compile')
 log=run('vsim',sim('state181_tb'),'states');assert 'PASS STATE181 edges=1056768 followups=1024' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'wire_bits=14016' in seq and 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 for label,needle,replacement in [
  ('verify', 'verified<=!state_error && state_verified;', 'verified<=state_verified;'),
  ('data', 'if(!error_hard && !error_response && !error_overlap && check_response)', 'if(!state_error && check_response)'),
  ('done', '&& !(pending && pending_command==8);','&& !(pending && (pending_command==8 || pending_command==9));')]:
  assert new.count(needle)==1;(a.out/('wrong-'+label+'.sv')).write_text(new.replace(needle,replacement))
  run('vlog',['-sv','wrong-'+label+'.sv'],label+'-compile');run('vsim',sim('state181_tb'),label+'-negative',True)
 names=['tools/nes_checkstate181.py','tools/test_nes_checkstate181.py','tools/test_nes_rawstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tools/test_nes_check165.py','tools/test_nes_counterpulse167.py','tests/nes-functional/tag165_tb.sv']
 r=dict(passed=True,same_edge=True,edges=1056768,followup_sequences=1024,wire_bits=14016,
  negative_cases=['error must clear verified','valid response data survives command error','CHECK_END preserves response done'],
  sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.candidate/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
  sources={n:sha(a.out/n) for n in ['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv']},public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
