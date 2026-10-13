# SPDX-License-Identifier: MIT
"""Explicit C2/C3 contract, late faults/reset, and legal SPI bit compatibility."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_commitstage167 import transform
from test_nes_counterpulse167 import bench as old_step
from test_nes_commandpulse165 import connected as old_connected
from test_nes_check165 import REGS
from test_nes_counterpulse167 import EXTRA

def bench():
 s=old_step()
 # C3 recomputes carry at C2; reference same-edge retirement needs the
 # already settled carry guaranteed by the legal SPI spacing.
 s=s.replace('next_carry8=carry;', 'next_carry8=(&n[7:0]);')
 s=s.replace('including inconsistent injected carries.', 'with settled carry at the acceptance edge.')
 s=s.replace('baseline_check165 refdut(.mem_clk(mem_clk)', 'reg ref_enable=1;wire ref_clk=mem_clk && ref_enable;\nbaseline_check165 refdut(.mem_clk(ref_clk)')
 s=s.replace(' dut.check_next=n;', ' ref_enable=1;dut.commit_clear=0;dut.commit_inc=0;\n dut.check_next=n;')
 line='if(dut.check_next!==refdut.check_next)$fatal(1,"CHECK165 mismatch check_next n=%h flags=%h op=%h",n,f,op);'
 assert s.count(line)==1;s=s.replace(line,'if(dut.check_next!==(reset?19\'d0:n))$fatal(1,"COMMIT167 early counter");')
 needle=' mem_clk=0;reset=0;#1;count++;'
 assert s.count(needle)==1
 s=s.replace(needle,''' mem_clk=0;reset=0;check_fault=0;boot_fault=0;check_response=0;ref_enable=0;
 #1;mem_clk=1;#1;
 if(dut.check_next!==refdut.check_next)$fatal(1,"COMMIT167 C3 result n=%h f=%h op=%h dut=%h ref=%h",n,f,op,dut.check_next,refdut.check_next);
 mem_clk=0;#1;count++;''')
 extra='''
integer late_cases=0;
task late(input integer action,input integer phase,input integer kind);
 reg [18:0] expected;
 begin
 mem_clk=0;reset=1;ref_enable=1;#1;mem_clk=1;#1;mem_clk=0;reset=0;
 check_fault=0;boot_fault=0;check_response=0;SPI_SS=1;
 dut.ss_sync=3;dut.ss_previous=1;dut.pending=1;dut.pending_command=action?8:4;
 dut.pending_counter_clear=!action;dut.pending_counter_inc=action;dut.decoded_error=0;dut.approved_pulse=0;
 dut.check_next=19'h12567;dut.next_carry8=0;dut.check_request_tag=19'h12567;
 dut.check_enable=1;dut.check_busy=1;dut.check_done=0;
 expected=action?19'h12568:0;
 // Phase0 error is present AT C2 and must prevent acceptance. Phase1 is
 // after acceptance but before C3; only reset may undo accepted metadata.
 if(phase==1)begin #1;mem_clk=1;#1;mem_clk=0;end
 case(kind)
  0:check_fault=1;
  1:begin check_response=1;check_response_address=19'h12566;end
  2:begin SPI_SS=0;dut.ss_sync=0;end
  3:reset=1;
  4:begin check_fault=1;check_response=1;check_response_address=19'h12566;end
  5:begin boot_fault=1;dut.check_enable=1;end
 endcase
 #1;mem_clk=1;#1;mem_clk=0;
 check_fault=0;check_response=0;boot_fault=0;SPI_SS=1;dut.ss_sync=3;reset=0;
 repeat(4)begin #1;mem_clk=1;#1;mem_clk=0;end
 if(dut.check_next!==(kind==3?19'd0:phase==0?19'h12567:expected))$fatal(1,"COMMIT167 late counter");
 if(kind==3)begin if(dut.fault||dut.commit_clear||dut.commit_inc)$fatal(1,"COMMIT167 reset queue");end
 else if(!dut.fault||dut.error_code!=(kind==0||kind==4||kind==5?9:kind==1?7:1)||dut.check_enable)$fatal(1,"COMMIT167 late error");
 late_cases++;
 end
endtask
'''
 s=s.replace('initial begin\n',extra+'initial begin\n',1)
 s=s.replace('$display("PASS COUNTERPULSE167 states=%0d",count);', '''for(integer a=0;a<2;a++)for(integer p=0;p<2;p++)for(integer k=0;k<6;k++)late(a,p,k);
 $display("PASS COMMIT167 states=%0d late=%0d",count,late_cases);''')
 return s

def connected():
 s=old_connected().replace('boot.loader.state=4;',"boot.loader.phase=16'h10;")
 s=s.replace("dut.approved_pulse=6'b010000;", "dut.approved_pulse=6'b010000;refdut.approved_pulse=6'b010000;")
 s=s.replace('wire spi_miso;reg [63:0] wire_rx;', 'wire spi_miso,ref_miso;reg [63:0] wire_rx;reg last_commit=0;integer compared_bits=0;')
 s=s.replace('.check_response_address(check_response_address),.check_data(check_data));','.check_response_address(check_response_address),.check_data(check_data),.spi_miso(ref_miso));')
 needle='if($countones(dut.approved_pulse)>1)$fatal(1,"PULSE165 multiple approved commands");'
 lag=['check_next','next_carry8','offset_matches_next','next_below_length','next_matches_length']
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"COMMIT167 sequential {n}");' for n in REGS+EXTRA if n not in lag)
 compare+='\nif(!(dut.counter_commit_pending || last_commit))begin\n'+'\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"COMMIT167 settled {n}");' for n in lag)+'\nend\nlast_commit=dut.counter_commit_pending;'
 assert needle in s;s=s.replace(needle,compare)
 needle='wire_rx={wire_rx[62:0],spi_miso};'
 s=s.replace(needle,'if(spi_miso!==ref_miso)$fatal(1,"COMMIT167 MISO bit");compared_bits++;'+needle)
 s=s.replace('  $display("PASS COMMANDSTAGE165', '  $display("PASS COMMIT167 wire_bits=%0d",compared_bits);\n  $display("PASS COMMANDSTAGE165')
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 (a.out/'step_tb.sv').write_text(bench());(a.out/'connected_tb.sv').write_text(connected())
 for n in ['nes_commitstage167.py','test_nes_commitstage167.py']:(a.out/n).write_bytes((ROOT/'tools'/n).read_bytes())
 def run(tool,args,label,expected=None):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if expected:assert expected in log and 'PASS COMMIT167' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','step_tb.sv','connected_tb.sv'],'compile')
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 steps=run('vsim',sim('check165_tb'),'steps');assert 'PASS COMMIT167 states=1048576 late=24' in steps
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq and 'wire_bits=14016' in seq
 for label,needle,replacement,expected in [
  ('fault','commit_inc<=counter_retire_ok && pending_counter_inc;','commit_inc<=pending && pending_counter_inc;','COMMIT167 C3 result'),
  ('late','else if(commit_inc)begin','else if(commit_inc && !check_fault)begin','COMMIT167 late counter'),
  ('overlap','captured || pending || counter_commit_pending','captured || pending','COMMIT167 late error')]:
  assert new.count(needle)==1
  (a.out/('wrong-'+label+'.sv')).write_text(new.replace(needle,replacement));run('vlog',['-sv','wrong-'+label+'.sv'],label+'-compile');run('vsim',sim('check165_tb'),label+'-negative',expected)
 names=['tools/nes_commitstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_counterpulse167.py','tools/test_nes_check165.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tests/nes-functional/tag165_tb.sv']
 r=dict(passed=True,conditional_transactions=1048576,late_boundaries=24,wire_bits=14016,counter_extra_cycles=1,same_edge=False,legal_spi_bytes_equal=True,spi_identity=0x74,min_ss_high_ns=2000,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],negative_cases=['C2 fault suppression','C3 accepted metadata survives late fault','C3 SS overlap rejected'],source_sha256=sha(a.candidate/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),sources={n:sha(a.out/n) for n in ['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','step_tb.sv','connected_tb.sv']},public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['sources','public_sources']}))
if __name__=='__main__':main()
