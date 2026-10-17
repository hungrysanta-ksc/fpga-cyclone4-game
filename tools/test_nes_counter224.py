# SPDX-License-Identifier: MIT
"""Counter C3 acceptance/C4 effects, live faults and complete serial regression."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_counter224 import transform
from test_nes_checkstate181 import STATE,bench as state_bench,connected

def bench():
 s=state_bench().replace('dut.check_busy=', 'dut.byte_last=0;refdut.byte_last=0;dut.check_busy=',1)
 seed='\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in STATE)
 cmp='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"COUNTER224 mismatch {n} f=%h action=%h prior=%h flip=%0d",f,action,prior,flip);' for n in STATE)
 task='''integer counter_cases=0;
 task counter_case(input [8:0] f,input [1:0] action,input [1:0] prior,input integer flip,input [18:0] value);
 reg eligible;reg [18:0] accepted_value,expected;reg [10:0] high_next;reg [7:0] low_next;
 begin
 '''+seed+'''
 dut.byte_last=0;refdut.byte_last=0;
 dut.pending=f[0];refdut.pending=f[0];
 dut.check_busy=f[1];refdut.check_busy=f[1];
 dut.check_enable=f[2];refdut.check_enable=f[2];
 dut.fault=f[3];refdut.fault=f[3];
 dut.ss_sync=f[4]?3:0;refdut.ss_sync=dut.ss_sync;
 dut.pending_command=4;refdut.pending_command=4; // STOP overlaps a live response.
 dut.pending_counter_clear=action[1];refdut.pending_counter_clear=action[1];
 dut.pending_counter_inc=action[0];refdut.pending_counter_inc=action[0];
 dut.commit_clear=prior[1];refdut.commit_clear=prior[1];
 dut.commit_inc=prior[0];refdut.commit_inc=prior[0];
 dut.check_request_tag=19'h52a69;refdut.check_request_tag=19'h52a69;
 dut.check_next=value;refdut.check_next=value;
 dut.next_carry8=&value[7:0];refdut.next_carry8=dut.next_carry8;
 reset=f[8];check_fault=f[7];boot_fault=f[6];check_response=f[5];
 check_response_address=19'h52a69 ^ (flip==19?19'd0:(19'd1<<flip));
 eligible=!f[8]&&!f[3]&&f[0]&&f[4]&&!f[7]&&!(f[2]&&f[6])&&
           !(f[5]&&(!f[2]||!f[1]||flip!=19));
 expected=f[8]?0:prior[1]?0:prior[0]?value+19'd1:value;
 #1;mem_clk=1;#1;
 '''+cmp+'''
 if({dut.commit_clear,dut.commit_inc} !== (eligible?action:2'd0))$fatal(1,"COUNTER224 acceptance oracle");
 if(dut.check_next!==expected)$fatal(1,"COUNTER224 prior commit oracle");
 accepted_value=expected;
 // Arbitrary adjacent prior/current commits are not legal >=2us SPI spacing.
 // For those differential states, model the existing registered carry from
 // value, rather than falsely demanding a fresh carry from accepted_value.
 high_next=accepted_value[18:8]+(&value[7:0]);low_next=accepted_value[7:0]+8'd1;
 expected=f[8]?0:(eligible&&action[1])?0:(eligible&&action[0])?{high_next,low_next}:accepted_value;
 // Valid accepted effects survive a newly arriving hard fault/SS overlap;
 // reset still cancels them. Clear wins over increment on simultaneous bits.
 mem_clk=0;#1;check_fault=1;boot_fault=1;SPI_SS=0;
 #1;mem_clk=1;#1;
 '''+cmp+'''
 if(dut.check_next!==expected)$fatal(1,"COUNTER224 delayed effect oracle");
 mem_clk=0;#1;counter_cases++;
 end endtask
 '''
 s=s.replace('initial begin\n',task+'''initial begin
 for(integer f=0;f<512;f++)for(integer a=0;a<4;a++)for(integer p=0;p<4;p++)for(integer bitno=0;bitno<20;bitno++)begin
  counter_case(f,a,p,bitno,19'd0);
  counter_case(f,a,p,bitno,19'hff);
  counter_case(f,a,p,bitno,19'h7ffff);
 end
 $display("PASS COUNTER224 cases=%0d edges=%0d",counter_cases,counter_cases*2);
 SPI_SS=1;
 ''',1)
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
  if negative:assert 'COUNTER224 mismatch' in log and 'PASS COUNTER224' not in log,(label,log[-3000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-3000:])
  return log
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv'],'compile')
 log=run('vsim',sim('state181_tb'),'states')
 assert 'PASS COUNTER224 cases=491520 edges=983040' in log and 'PASS STATE181 edges=1056768 followups=1024' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'wire_bits=14016' in seq and 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 for label,needle,replacement in [('high','counter_low & counter_high &','counter_low &'),('low','counter_low & counter_high &','counter_high &'),('pending','!fault && pending && ss_sync[1]','!fault && ss_sync[1]')]:
  assert new.count(needle)==1;(a.out/('wrong-'+label+'.sv')).write_text(new.replace(needle,replacement))
  run('vlog',['-sv','wrong-'+label+'.sv'],label+'-compile');run('vsim',sim('state181_tb'),label+'-negative',True)
 names=['tools/nes_counter224.py','tools/test_nes_counter224.py','tools/test_nes_checkstate181.py','tools/test_nes_rawstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tools/test_nes_check165.py','tools/test_nes_counterpulse167.py','tests/nes-functional/tag165_tb.sv']
 result=dict(passed=True,same_edge=True,counter_cases=491520,counter_edges=983040,state_edges=1056768,followups=1024,
  negatives=['upper mismatch ignored','lower mismatch ignored','missing pending gate'],
  serial_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.candidate/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
  sources={n:sha(a.out/n) for n in ['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv']},public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k not in ['sources','public_sources']}))
if __name__=='__main__':main()
