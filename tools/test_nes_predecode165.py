# SPDX-License-Identifier: MIT
"""Capture validity plus same-edge retirement equivalence; two causal controls."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_predecode165 import transform,specialize,masked
from test_nes_check165 import bench as old_bench,REGS

def bench():
 s=old_bench()
 at=' check_response_address=f[9]?(n^19\'h40001):n;'
 assert s.count(at)==1
 s=s.replace(at,at+'''
 dut.pending_counter_clear=!f[7] && !f[8] && (op==0 || op==4 || op==6);
 dut.pending_counter_inc=!f[7] && !f[8] && op==8;''')
 seed='\n'.join('dut.'+n+"='0; refdut."+n+"='0;" for n in REGS)
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"CAPTURE165 mismatch {n}");' for n in REGS)
 task='''integer captures=0;
task capture(input [7:0] cmd,input [6:0] f,input [7:0] argument,input integer region);
begin
'''+seed+'''
 reset=0;check_fault=0;boot_fault=f[6];check_response=0;
 loaded=!f[5];run_enable=0;load_ready=!f[4];check_ready=1;
 dut.pending_counter_clear=1;dut.pending_counter_inc=1;
 dut.ss_sync=3;refdut.ss_sync=3;dut.ss_previous=0;refdut.ss_previous=0;
 dut.command=cmd;refdut.command=cmd;
 dut.offset=region==0?0:region==1?{5'd0,loaded_bytes}:24'd5;refdut.offset=dut.offset;
 dut.arg=argument;refdut.arg=argument;
 dut.arg_not=f[3]?argument:~argument;refdut.arg_not=dut.arg_not;
 dut.tail=f[2]?8'h5a:8'ha5;refdut.tail=dut.tail;
 dut.crc=8'h59;refdut.crc=8'h59;
 dut.received_crc=f[1]?8'h95:8'h59;refdut.received_crc=dut.received_crc;
 dut.byte_count=f[0]?7:8;refdut.byte_count=dut.byte_count;
 dut.bit_count=f[6]?1:0;refdut.bit_count=dut.bit_count;
 dut.check_enable=f[4];refdut.check_enable=dut.check_enable;
 dut.check_busy=f[5];refdut.check_busy=dut.check_busy;
 dut.check_done=!f[5];refdut.check_done=dut.check_done;
 dut.verified=!f[6];refdut.verified=dut.verified;
 dut.offset_matches_next=!f[6];refdut.offset_matches_next=dut.offset_matches_next;
 dut.next_below_length=!f[5];refdut.next_below_length=dut.next_below_length;
 dut.next_matches_length=f[5];refdut.next_matches_length=dut.next_matches_length;
 dut.checked_data=argument;refdut.checked_data=argument;
 #1;mem_clk=1;#1;
'''+compare+'''
 if(refdut.pending)begin
  if(dut.pending_counter_clear !== (refdut.pending_header_error==0 && refdut.pending_causes==0 &&
    (refdut.pending_command==0 || refdut.pending_command==4 || refdut.pending_command==6)))$fatal(1,"CAPTURE165 clear predicate");
  if(dut.pending_counter_inc !== (refdut.pending_header_error==0 && refdut.pending_causes==0 &&
    refdut.pending_command==8))$fatal(1,"CAPTURE165 inc predicate");
 end
 mem_clk=0;#1;captures++;
end endtask
'''
 s=s.replace('initial begin\n // Exhaustive',task+'initial begin\n // Exhaustive',1)
 s=s.replace('$display("PASS CHECK165 states=%0d",count);', '''for(integer c=0;c<256;c++)for(integer f=0;f<128;f++)for(integer a=0;a<4;a++)
  for(integer region=0;region<3;region++)capture(c,f,a==0?0:a==1?2:a==2?8'h96:8'hff,region);
 $display("PASS PREDECODE165 states=%0d captures=%0d",count,captures);''')
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.prepared/'nes_rom_spi.sv').read_text();assert new in [specialize(transform(old)),masked(specialize(transform(old)))]
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1))
 (a.out/'candidate.sv').write_text(new);(a.out/'check165_tb.sv').write_text(bench())
 def run(tool,args,label,expected=None):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if expected:assert expected in log and 'PASS PREDECODE165' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','check165_tb.sv'],'compile')
 args=['-c','check165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',args,'equivalence');assert 'PASS PREDECODE165 states=786432 captures=393216' in log
 for name,oldtext,newtext,expected in [('fault','&& !check_fault &&',"&& 1'b1 &&",'CHECK165 mismatch check_next'),('header','pending_counter_inc<=counter_header_ok &&','pending_counter_inc<=','CAPTURE165 inc predicate')]:
  assert new.count(oldtext)==1
  (a.out/('wrong-'+name+'.sv')).write_text(new.replace(oldtext,newtext))
  run('vlog',['-sv','wrong-'+name+'.sv'],name+'-compile');run('vsim',args,name+'-negative',expected)
 result=dict(passed=True,states=786432,captures=393216,wrong_fault_gate_rejected=True,wrong_header_gate_rejected=True,source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in ['tools/nes_predecode165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
