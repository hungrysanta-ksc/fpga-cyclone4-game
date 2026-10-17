# SPDX-License-Identifier: MIT
"""Same-edge SPI differential states, bit boundaries and real wire transactions."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_retire219 import spi as transform
from test_nes_checkstate181 import STATE,bench as state_bench,connected

def bench():
 s=state_bench().replace('dut.check_busy=', 'dut.byte_last=0;refdut.byte_last=0;dut.check_busy=',1)
 seed='\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in STATE)
 cmp='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"RETIRE219 mismatch {n} flags=%h pulse=%h flip=%0d",f,pulse,flip);' for n in STATE)
 task="""integer retire_checks=0;
 task retire_case(input [7:0] f,input [5:0] pulse,input integer flip);
 begin
 """+seed+"""
 dut.byte_last=0;refdut.byte_last=0;
 reset=f[7];check_fault=f[6];boot_fault=f[5];check_response=f[4];
 dut.ss_sync=f[0]?3:0;refdut.ss_sync=dut.ss_sync;
 dut.fault=f[1];refdut.fault=f[1];
 dut.check_enable=f[2];refdut.check_enable=f[2];
 dut.check_busy=f[3];refdut.check_busy=f[3];
 dut.check_request_tag=19'h52a69;refdut.check_request_tag=19'h52a69;
 check_response_address=19'h52a69 ^ (flip==19?19'd0:(19'd1<<flip));
 dut.approved_pulse=pulse;refdut.approved_pulse=pulse;
 #1;mem_clk=1;#1;
 """+cmp+"""
 mem_clk=0;#1;retire_checks++;
 end endtask
 """
 s=s.replace('initial begin\n',task+'initial begin\n',1)
 s=s.replace(' $display("PASS STATE181', ' for(integer f=0;f<256;f++)for(integer p=0;p<64;p++)for(integer b=0;b<20;b++)retire_case(f,p,b);\n $display("PASS RETIRE219 checks=%0d",retire_checks);\n $display("PASS STATE181')
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 (a.out/'state_tb.sv').write_text(bench());(a.out/'connected_tb.sv').write_text(connected())
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert 'RETIRE219 mismatch' in log or 'STATE181 mismatch' in log,(label,log[-3000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-3000:])
  return log
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv'],'compile')
 log=run('vsim',sim('state181_tb'),'states');assert 'PASS STATE181 edges=1056768 followups=1024' in log and 'checks=327680' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'wire_bits=14016' in seq and 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 for label,needle,replacement in [('high','retire_low & retire_high &','retire_low &'),('low','retire_low & retire_high &','retire_high &')]:
  assert new.count(needle)==1;(a.out/('wrong-'+label+'.sv')).write_text(new.replace(needle,replacement))
  run('vlog',['-sv','wrong-'+label+'.sv'],label+'-compile');run('vsim',sim('state181_tb'),label+'-negative',True)
 r=dict(passed=True,same_edge=True,edges=1056768,followup_sequences=1024,retire_checks=327680,wire_bits=14016,negative_cases=['upper mismatch ignored','lower mismatch ignored'],
  sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.candidate/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
  sources={n:sha(a.out/n) for n in ['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv']},
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_retire219.py','tools/test_nes_retire219.py','tools/test_nes_checkstate181.py','tools/test_nes_rawstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tools/test_nes_check165.py','tools/test_nes_counterpulse167.py','tests/nes-functional/tag165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['sources','public_sources']}))
if __name__=='__main__':main()
