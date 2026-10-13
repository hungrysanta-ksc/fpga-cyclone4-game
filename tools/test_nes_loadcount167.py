# SPDX-License-Identifier: MIT
"""Loader edge/pin equivalence and actual SPI with both167 changes connected."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_loadcount167 import transform
from test_nes_directloader165 import bench as prior_bench
from test_nes_counterpulse167 import connected

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','pulse-test','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.candidate/'nes_rom_loader.sv').read_text();assert new==transform(old)
 t=json.loads((a.pulse_test/'result.json').read_bytes());assert t['passed'] and t['source_sha256']==sha(a.candidate/'nes_rom_spi.sv')
 a.out.mkdir();(a.out/'loader-reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #',1));(a.out/'nes_rom_loader.sv').write_bytes((a.candidate/'nes_rom_loader.sv').read_bytes())
 s=prior_bench().replace('refdut.state=state;',"refdut.phase=16'b1<<state;")
 # Reuse command/phase coverage and add every19bit counter value at RELEASE.
 needle='  // Seeded one-step enumeration is followed by actual BEGIN/byte/phase sequences.'
 assert needle in s
 # The existing bench covers zero, total-1, total. Arithmetic itself is
 # exhaustively checked with actual register logic below in a separate top.
 (a.out/'loader_tb.sv').write_text(s)
 for n in ['nes_rom_boot.sv','nes_rom_physical.sv','nes_rom_spi.sv']:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 (a.out/'reference.sv').write_text((a.baseline/'nes_rom_spi.sv').read_text().replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'connected_tb.sv').write_text(connected())
 arithmetic='''`timescale 1ns/1ps
module arithmetic_tb;
reg mem_clk=0,reset=1;
nes_rom_loader dut(.mem_clk(mem_clk),.reset(reset),.load_begin(1'b0),.load_chr32(1'b0),.load_valid(1'b0),.load_end(1'b0),.start(1'b0),.stop(1'b0),.load_data(8'd0),.commands_blocked(1'b0));
initial begin
#1;reset=0;
for(integer n=0;n<524288;n++)begin
 dut.release_reset=0;dut.fault=0;dut.phase=16'h100;dut.remaining=1;dut.terminal=1;dut.loaded_bytes=n;dut.count_complete=0;
 #1;mem_clk=1;#1;
 if(dut.loaded_bytes !== ((n+1)&19'h7ffff) || dut.count_complete !== (n==19'h5ffff))$fatal(1,"LOADCOUNT167 increment %h",n);
 mem_clk=0;
end
$display("PASS LOADCOUNT167 524288 increments");$finish;
end
endmodule
'''
 (a.out/'arithmetic_tb.sv').write_text(arithmetic)
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal: DIFF131' in log and 'PASS STATE165' not in log,log[-2000:]
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','loader-reference.sv','nes_rom_loader.sv','loader_tb.sv','arithmetic_tb.sv','reference.sv','nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_physical.sv','connected_tb.sv'],'compile')
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 assert 'PASS STATE165 states=294912 sequences=1056' in run('vsim',sim('counter131_diff_tb'),'loader')
 assert 'PASS LOADCOUNT167 524288 increments' in run('vsim',sim('arithmetic_tb'),'arithmetic')
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 (a.out/'wrong.sv').write_text(new.replace('wire count_clear=active_reset || count_stop || count_begin;','wire count_clear=active_reset || count_begin;'))
 run('vlog',['-sv','wrong.sv'],'negative-compile');run('vsim',sim('counter131_diff_tb'),'negative',True)
 names=['tools/nes_loadcount167.py','tools/test_nes_loadcount167.py','tools/test_nes_directloader165.py','tools/test_nes_state165.py','tools/test_nes_drain165.py','tests/nes-functional/counter131_diff_tb.sv','tools/test_nes_counterpulse167.py']
 r=dict(passed=True,states=294912,sequences=1056,increments=524288,same_edge=True,stop_clear_negative=True,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],pulse_test_sha256=sha(a.pulse_test/'result.json'),sources={n:sha(a.candidate/n) for n in ['nes_rom_loader.sv','nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_physical.sv']},reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
