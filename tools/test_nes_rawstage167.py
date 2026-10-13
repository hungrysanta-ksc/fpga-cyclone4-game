# SPDX-License-Identifier: MIT
"""C0 sampling contract, C1-C3 cancellation and legal SPI wire equivalence."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_rawstage167 import transform
from test_nes_check165 import REGS
from test_nes_counterpulse167 import EXTRA
from test_nes_commitstage167 import bench as commit_bench,connected as commit_connected
from test_nes_commandstage165 import EFFECTS

def bench():
 old=commit_bench();s=old[:old.index('integer count=0;')]
 seed='\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in dict.fromkeys(REGS+EXTRA+['pending_counter_clear','pending_counter_inc','commit_clear','commit_inc']))
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"RAW167 effect {n} cmd=%h hdr=%h life=%h ext=%h",cmd,h,l,e);' for n in EFFECTS)
 s+='''integer captures=0,boundaries=0;
task edge;#1;mem_clk=1;#1;endtask
task low;mem_clk=0;#1;endtask
task capture(input [7:0] cmd,input [4:0] h,input [6:0] l,input [3:0] e,input [7:0] argument,input integer region,input [18:0] length);
begin
'''+seed+'''
 dut.sampled=0;dut.raw_causes=0;dut.raw_select=0;dut.raw_loaded=0;dut.raw_run=0;dut.raw_ready=0;dut.raw_load_ready=0;
 reset=0;ref_enable=1;check_fault=0;boot_fault=0;check_response=0;SPI_SS=1;SPI_SCK=0;
 loaded=e[0];run_enable=e[1];check_ready=e[2];load_ready=e[3];loaded_bytes=length;
 dut.ss_sync=3;refdut.ss_sync=3;dut.ss_previous=0;refdut.ss_previous=0;
 dut.command=cmd;refdut.command=cmd;
 dut.offset_zero_command=cmd==8'h60;refdut.offset_zero_command=dut.offset_zero_command;
 dut.offset_length_command=cmd>=8'h61&&cmd<=8'h64;refdut.offset_length_command=dut.offset_length_command;
 dut.offset=region==0?0:region==1?{5'd0,length}:region==2?24'd5:({5'd0,length}^(24'd1<<(region-3)));refdut.offset=dut.offset;
 dut.arg=argument;refdut.arg=argument;
 dut.arg_not=h[3]?argument:~argument;refdut.arg_not=dut.arg_not;
 dut.tail=h[2]?8'h5a:8'ha5;refdut.tail=dut.tail;
 dut.crc=8'h59;refdut.crc=8'h59;dut.received_crc=h[1]?8'h95:8'h59;refdut.received_crc=dut.received_crc;
 dut.byte_count=h[0]?7:8;refdut.byte_count=dut.byte_count;dut.bit_count=h[4]?1:0;refdut.bit_count=dut.bit_count;
 dut.check_enable=l[0];refdut.check_enable=l[0];dut.check_busy=l[1];refdut.check_busy=l[1];dut.check_done=l[2];refdut.check_done=l[2];
 dut.verified=l[3];refdut.verified=l[3];dut.offset_matches_next=l[4];refdut.offset_matches_next=l[4];
 dut.next_below_length=l[5];refdut.next_below_length=l[5];dut.next_matches_length=l[6];refdut.next_matches_length=l[6];
 dut.checked_data=argument;refdut.checked_data=argument;dut.check_next=19'h12567;refdut.check_next=19'h12567;
 dut.check_request_tag=19'h12567;refdut.check_request_tag=19'h12567;
 edge();
 if(dut.sampled!==refdut.captured || dut.pending_command!==refdut.pending_command || dut.pending_header_error!==refdut.pending_header_error)$fatal(1,"RAW167 C0 capture");
 low();ref_enable=0;
 // Change ALL external eligibility/length immediately after C0. C1 must
 // aggregate saved values, not these new live values.
 loaded=~loaded;run_enable=~run_enable;check_ready=~check_ready;load_ready=~load_ready;loaded_bytes=length^19'h41234;
 edge();
 if(dut.pending_causes!==refdut.pending_causes)$fatal(1,"RAW167 C1 causes cmd=%h h=%h l=%h e=%h dut=%h ref=%h",cmd,h,l,e,dut.pending_causes,refdut.pending_causes);
 if(dut.load_begin||dut.load_valid||dut.load_end||dut.start||dut.stop||dut.check_request)$fatal(1,"RAW167 early effect");
 low();ref_enable=1;
 repeat(3)begin edge();
'''+compare+'''
 low();end
 captures++;
end endtask
task boundary(input integer phase,input integer kind,input integer op);
 reset=1;ref_enable=1;mem_clk=0;edge();low();reset=0;
 check_fault=0;boot_fault=0;check_response=0;SPI_SS=1;
 dut.ss_sync=3;dut.ss_previous=1;dut.sampled=1;dut.pending_command=op;dut.pending_arg=2;
 dut.pending_header_error=0;dut.raw_causes=0;dut.raw_select=0;
 dut.check_next=19'h12567;dut.check_request_tag=19'h12567;
 dut.check_enable=1;dut.check_busy=1;dut.check_done=0;
 repeat(phase)begin edge();low();end
 case(kind)
  0:check_fault=1;
  1:begin check_response=1;check_response_address=19'h12566;end
  2:begin SPI_SS=0;dut.ss_sync=0;end
  3:reset=1;
  4:begin check_fault=1;check_response=1;check_response_address=19'h12566;end
  5:boot_fault=1;
 endcase
 edge();
 if(dut.load_begin||dut.load_valid||dut.load_end||dut.start||dut.stop||dut.check_request)$fatal(1,"RAW167 same-edge cancellation");
 low();check_fault=0;check_response=0;boot_fault=0;reset=0;SPI_SS=1;dut.ss_sync=3;
 repeat(6)begin edge();
  if(dut.load_begin||dut.load_valid||dut.load_end||dut.start||dut.stop||dut.check_request)$fatal(1,"RAW167 cancelled escaped");
  low();
 end
 if(kind==3)begin
  if(dut.fault||dut.check_next!=0||dut.sampled||dut.captured||dut.pending||dut.commit_clear||dut.commit_inc)$fatal(1,"RAW167 reset queue");
 end else if(!dut.fault||dut.error_code!=(kind==0||kind==4||kind==5?9:kind==1?7:1)||dut.check_next!=19'h12567||dut.check_enable)
  $fatal(1,"RAW167 cancellation priority phase=%0d kind=%0d op=%0d",phase,kind,op);
 boundaries++;
endtask
'''
 # Retain the established acceptance/late-fault contract, including reset
 # between counter acceptance and commit; seeded pending bypasses early stages.
 s+=old[old.index('integer late_cases=0;'):old.index('initial begin\n // Exhaustive')]
 s+='''initial begin
 if(!$test$plusargs("BOUNDARY_ONLY"))begin
  for(integer c=0;c<256;c++)for(integer h=0;h<32;h++)for(integer a=0;a<4;a++)for(integer r=0;r<3;r++)
   capture(c,h,7'h78,4'hd,a==0?0:a==1?2:a==2?8'h96:8'hff,r,19'h60000);
  for(integer c=0;c<11;c++)for(integer l=0;l<128;l++)for(integer e=0;e<16;e++)for(integer a=0;a<4;a++)for(integer r=0;r<3;r++)
   capture(8'h60+c,0,l,e,a==0?0:a==1?2:a==2?8'h96:8'hff,r,19'h60000);
  for(integer len=0;len<7;len++)for(integer b=0;b<25;b++)for(integer c=0;c<3;c++)
   capture(c==0?8'h64:c==1?8'h60:8'h66,0,7'h78,4'hd,c==1?2:0,b==24?1:b+3,len==0?0:len==1?1:len==2?19'hff:len==3?19'h100:len==4?19'h5ffff:len==5?19'h60000:19'h7ffff);
 end
 for(integer p=0;p<3;p++)for(integer k=0;k<6;k++)for(integer op=0;op<10;op++)boundary(p,k,op);
 for(integer a=0;a<2;a++)for(integer p=0;p<2;p++)for(integer k=0;k<6;k++)late(a,p,k);
 $display("PASS RAW167 captures=%0d boundaries=%0d late=%0d",captures,boundaries,late_cases);$finish;
end
endmodule
'''
 return s.replace('task edge;', 'task tick_up;').replace('edge();','tick_up();')

def connected():
 s=commit_connected()
 a=s.index('if(dut.check_busy!==refdut.check_busy)');b=s.index('last_commit=dut.counter_commit_pending;',a)+len('last_commit=dut.counter_commit_pending;')
 # Command stages differ; compare actual external bits instead of per-edge
 # internal registers. The real boot/reader remains connected to the DUT.
 return s[:a]+'// Explicitly shifted command acceptance; wire comparison below.'+s[b:]

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 (a.out/'capture_tb.sv').write_text(bench());(a.out/'connected_tb.sv').write_text(connected())
 for n in ['nes_rawstage167.py','test_nes_rawstage167.py']:(a.out/n).write_bytes((ROOT/'tools'/n).read_bytes())
 def run(tool,args,label,expected=None):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if expected:assert expected in log and 'PASS RAW167' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 def sim(top,short=False):return ['-c',top,*(['+BOUNDARY_ONLY'] if short else []),'-do','onerror {quit -code 1}; run -all; quit -f']
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','capture_tb.sv','connected_tb.sv'],'compile')
 log=run('vsim',sim('check165_tb'),'capture');assert 'PASS RAW167 captures=369165 boundaries=180 late=24' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'wire_bits=14016' in seq and 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 for label,needle,replacement,expected,short in [
  ('live', 'raw_select[2] && !raw_ready','raw_select[2] && !check_ready','RAW167 C1 causes',False),
  ('overlap','sampled || captured || pending || counter_commit_pending','captured || pending || counter_commit_pending','RAW167 cancelled escaped',True),
  ('fault','wire command_retire_ok=!fault && ss_sync[1] && !check_fault &&','wire command_retire_ok=!fault && ss_sync[1] &&','RAW167 same-edge cancellation',True)]:
  assert new.count(needle)==1; (a.out/('wrong-'+label+'.sv')).write_text(new.replace(needle,replacement))
  run('vlog',['-sv','wrong-'+label+'.sv'],label+'-compile');run('vsim',sim('check165_tb',short),label+'-negative',expected)
 names=['tools/nes_rawstage167.py','tools/test_nes_rawstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_counterpulse167.py','tools/test_nes_check165.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tests/nes-functional/tag165_tb.sv']
 r=dict(passed=True,captures=369165,cancel_boundaries=180,late_boundaries=24,wire_bits=14016,extra_command_cycles=1,same_edge=False,
  source_sha256=sha(a.candidate/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
  sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],negative_cases=['live eligibility after capture','C1 SS overlap','retirement hard fault'],
  sources={n:sha(a.out/n) for n in ['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','capture_tb.sv','connected_tb.sv']},public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['sources','public_sources']}))
if __name__=='__main__':main()
