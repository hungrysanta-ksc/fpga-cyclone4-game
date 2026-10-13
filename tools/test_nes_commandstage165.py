# SPDX-License-Identifier: MIT
"""Latency-aware transaction comparison and cancellation at both queued stages."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_commandstage165 import transform
from test_nes_balancedlength165 import bench as old_bench

EFFECTS='check_busy check_done verified check_next checked_data load_begin load_chr32 load_valid load_end start stop load_data fault error_code check_enable check_request'.split()

def bench():
 s=old_bench()
 s=s.replace('baseline_check165 refdut(.mem_clk(mem_clk)', 'reg ref_enable=1; wire ref_clk=mem_clk && ref_enable;\nbaseline_check165 refdut(.mem_clk(ref_clk)')
 s=s.replace(' reset=0;check_fault=0;boot_fault=f[6];check_response=0;', ' ref_enable=1;dut.captured=0;dut.decoded_error=0;\n reset=0;check_fault=0;boot_fault=f[6];check_response=0;')
 s=re.sub(r'if\(dut\.pending!==refdut\.pending\)\$fatal\(1,"CAPTURE165 mismatch pending"\);','',s)
 a=s.index(' if(refdut.pending)begin');b=s.index(' mem_clk=0;#1;',a);s=s[:a]+s[b:]
 a=s.index('if(dut.check_busy!==refdut.check_busy)$fatal(1,"STOPCLEAR165 retirement');b=s.index(' mem_clk=0;#1;captures++;',a)
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"STAGE165 result {n} cmd=%h flags=%h",cmd,f);' for n in EFFECTS)
 s=s[:a]+'''if(dut.load_begin||dut.load_valid||dut.load_end||dut.start||dut.stop||dut.check_request)
 $fatal(1,"STAGE165 premature effect");
 // Reference is held AFTER its original retirement; candidate advances one
 // extra clock. This is transaction-result equivalence, NOT edge equivalence.
 mem_clk=0;#1;ref_enable=0;#1;mem_clk=1;#1;
'''+compare+'\n'+s[b:]
 extra='''
integer boundaries=0;
task boundary(input integer phase,input integer kind,input integer op);
 reset=1;mem_clk=0;ref_enable=1;#1;mem_clk=1;#1;mem_clk=0;reset=0;
 check_fault=0;boot_fault=0;check_response=0;SPI_SS=1;
 dut.ss_sync=3;dut.ss_previous=1;dut.captured=1;
 dut.pending=0;dut.pending_command=op;dut.pending_header_error=0;dut.pending_causes=0;
 dut.check_next=19'h12567;dut.check_request_tag=19'h12567;
 dut.check_enable=1;dut.check_busy=1;dut.check_done=0;
 dut.pending_counter_clear=0;dut.pending_counter_inc=0;
 if(phase==1)begin #1;mem_clk=1;#1;mem_clk=0;end
 case(kind)
  0:check_fault=1;
  1:begin check_response=1;check_response_address=19'h12566;end
  2:begin SPI_SS=0;dut.ss_sync=0;end
  3:reset=1;
  4:begin check_fault=1;check_response=1;check_response_address=19'h12566;end
  5:boot_fault=1;
 endcase
 #1;mem_clk=1;#1;mem_clk=0;
 check_fault=0;check_response=0;boot_fault=0;reset=0;SPI_SS=1;
 // A one-cycle synchronized overlap must remain fatal after SS returns high.
 if(kind==2)dut.ss_sync=3;
 repeat(5)begin #1;mem_clk=1;#1;
  if(dut.load_begin||dut.load_valid||dut.load_end||dut.start||dut.stop||dut.check_request)
   $fatal(1,"STAGE165 cancelled command escaped phase=%0d kind=%0d op=%0d",phase,kind,op);
  mem_clk=0;
 end
 if(kind==3)begin
  if(dut.fault||dut.check_next!=0||dut.check_enable)$fatal(1,"STAGE165 reset");
 end else if(!dut.fault||dut.error_code!=(kind==0||kind==4||kind==5?9:kind==1?7:1)||dut.check_next!=19'h12567||dut.check_enable)
  $fatal(1,"STAGE165 cancellation priority phase=%0d kind=%0d op=%0d",phase,kind,op);
 boundaries++;
endtask
'''
 s=s.replace('initial begin\n',extra+'initial begin\n',1)
 s=s.replace('$display("PASS STOPCLEAR165 captures=%0d",captures);', '''for(integer phase=0;phase<2;phase++)for(integer kind=0;kind<6;kind++)for(integer op=0;op<10;op++)boundary(phase,kind,op);
 $display("PASS COMMANDSTAGE165 captures=%0d boundaries=%0d",captures,boundaries);''')
 return s

def connected():
 s=(ROOT/'tests/nes-functional/tag165_tb.sv').read_text()
 # Actual boot/reader use candidate pulses. Reference has a different latency
 # and is not an oracle for per-edge responses of this connected test.
 s=s.replace('// COMPARE_ALL_REGISTERS','// No same-edge comparison: the contract adds a clock.')
 s=s.replace('dut.pending_header_error=0;refdut.pending_header_error=0;', 'dut.decoded_error=0;dut.pending_header_error=0;refdut.pending_header_error=0;')
 s=s.replace('nes_rom_spi_check dut(.*,.spi_miso(),.spi_selected());', 'wire spi_miso;reg [63:0] wire_rx;integer wire_frames=0;\n nes_rom_spi_check dut(.*,.spi_selected());')
 s=s.replace('  SPI_SS=0;#2000;', '  #2000;SPI_SS=0;#2000;wire_rx=0;')
 s=s.replace('#190.476;SPI_SCK=0;end', '#190.476;wire_rx={wire_rx[62:0],spi_miso};SPI_SCK=0;end')
 s=s.replace('  #2000;SPI_SS=1;', '''  #2000;SPI_SS=1;wire_frames++;
  if(wire_rx[55:48]!==8'h74)$fatal(1,"STAGE165 wire identity %h",wire_rx);
''')
 s=s.replace(' initial begin\n  normal(0);', ''' initial begin
  fresh();frame(8'h60,0,2);#2000;
  if(fault||!load_ready||loaded_bytes!=0)$fatal(1,"STAGE165 wire BEGIN");
  frame(8'h61,0,8'h96);#2000;
  if(fault||!load_ready||loaded_bytes!=1)$fatal(1,"STAGE165 wire DATA");
  frame(8'h65,0,0);#2000;
  if(wire_rx[31:8]!=1||wire_rx[39:32]!=0)$fatal(1,"STAGE165 wire post-DATA snapshot");
  frame(8'h64,1,0);#2000;
  if(fault||check_enable||run_enable)$fatal(1,"STAGE165 wire STOP");
  frame(8'h65,0,0);#2000;
  if(wire_rx[31:8]!=0||wire_rx[47:40]!=0)$fatal(1,"STAGE165 wire post-STOP snapshot");
  normal(0);''')
 s=s.replace('  $display("PASS TAG165', '  $display("PASS COMMANDSTAGE165 wire_frames=%0d sck_hz=2625000 ss_gap_ns=2000",wire_frames);\n  $display("PASS TAG165')
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
 needle='(captured || pending) && !ss_sync[1]';assert new.count(needle)==1
 (a.out/'wrong-overlap.sv').write_text(new.replace(needle,'pending && !ss_sync[1]'))
 run('vlog',['-sv','wrong-overlap.sv'],'negative-compile');run('vsim',sim('check165_tb'),'negative','STAGE165 cancelled command escaped')
 names=['tools/nes_commandstage165.py','tools/test_nes_commandstage165.py','tools/test_nes_balancedlength165.py','tools/test_nes_stopclear165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py','tests/nes-functional/tag165_tb.sv']
 result=dict(passed=True,captures=393741,boundaries=120,added_mem_cycles=1,transaction_result_comparison=True,same_edge_equivalence=False,wrong_overlap_rejected=True,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
