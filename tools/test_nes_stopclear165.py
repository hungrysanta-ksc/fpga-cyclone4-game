# SPDX-License-Identifier: MIT
"""Same-edge capture/retirement and connected SPI/boot regression for STOP clear."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_stopclear165 import transform
from test_nes_predecode165 import bench as capture_bench
from test_nes_check165 import REGS

def bench():
 s=capture_bench()
 a=s.index('task step(');b=s.index('integer captures=0;',a);s=s[:a]+s[b:]
 a=s.index(' // Exhaustive counter');b=s.index('for(integer c=0;c<256;',a);s=s[:a]+s[b:]
 s=s.replace(' dut.pending_counter_clear=1;dut.pending_counter_inc=1;', ''' dut.pending_other_clear=1;dut.pending_stop_clear=1;dut.pending_stop_offset_ok=1;
 refdut.pending_counter_clear=1;dut.pending_counter_inc=1;refdut.pending_counter_inc=1;
 dut.check_next=19'h12567;refdut.check_next=19'h12567;''')
 s=s.replace("region==0?0:region==1?{5'd0,loaded_bytes}:24'd5", "region==0?0:region==1?{5'd0,loaded_bytes}:region==2?24'd5:({5'd0,loaded_bytes} ^ (24'd1 << (region-3)))")
 needle=' mem_clk=0;#1;captures++;'
 assert s.count(needle)==1
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"STOPCLEAR165 retirement {n}");' for n in REGS+['pending_counter_clear','pending_counter_inc'])
 s=s.replace(needle,''' if(dut.pending_counter_clear!==refdut.pending_counter_clear)$fatal(1,"STOPCLEAR165 capture predicate");
 mem_clk=0;#1;
 // Change the live length after capture. Retirement must use captured operands.
 loaded_bytes=loaded_bytes^19'h41234;
 #1;mem_clk=1;#1;
'''+compare+'''
 mem_clk=0;#1;captures++;''')
 needle=' $display("PASS PREDECODE165 states=%0d captures=%0d",count,captures);'
 extra=''' for(integer len=0;len<7;len++)for(integer bitpos=0;bitpos<25;bitpos++)for(integer c=0;c<3;c++)begin
  loaded_bytes=len==0?0:len==1?1:len==2?19'hff:len==3?19'h100:len==4?19'h5ffff:len==5?19'h60000:19'h7ffff;
  capture(c==0?8'h64:c==1?8'h60:8'h66,0,c==1?2:0,bitpos==24?1:bitpos+3);
 end
 $display("PASS STOPCLEAR165 captures=%0d",captures);'''
 assert s.count(needle)==1
 return s.replace(needle,extra)

def connected():
 s=(ROOT/'tests/nes-functional/tag165_tb.sv').read_text()
 s=s.replace('dut.pending_counter_clear=1;refdut.pending_counter_clear=1;', 'dut.pending_other_clear=0;dut.pending_stop_clear=1;dut.pending_stop_offset_ok=1;refdut.pending_counter_clear=1;')
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"STOPCLEAR165 connected {n}");' for n in REGS+['pending_counter_clear','pending_counter_inc','check_request_tag'])
 return s.replace('// COMPARE_ALL_REGISTERS',compare)

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
 log=run('vsim',sim('check165_tb'),'capture');assert 'PASS STOPCLEAR165 captures=393741' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 needle='pending_stop_clear && pending_stop_offset_ok';assert new.count(needle)==1
 (a.out/'wrong-offset.sv').write_text(new.replace(needle,'pending_stop_clear'))
 run('vlog',['-sv','wrong-offset.sv'],'negative-compile');run('vsim',sim('check165_tb'),'negative','CAPTURE165 clear predicate')
 names=['tools/nes_stopclear165.py','tools/test_nes_stopclear165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py','tests/nes-functional/tag165_tb.sv']
 result=dict(passed=True,captures=393741,retirement_live_length_changed=True,wrong_offset_rejected=True,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
