# SPDX-License-Identifier: MIT
"""Actual epoch207/217 same-edge differential and existing stopped-clock admission."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_epoch217 import ROOT,BASE,sha,transform

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=BASE/'probes/nes-wait216/source02/nes_source_epoch207.sv';new=BASE/'probes/nes-loader217/source02/nes_source_epoch207.sv';assert new.read_text()==transform(old.read_text())
 pins={str(f.relative_to(BASE)):sha(f) for f in [old,new]}
 shutil.copyfile(new,a.out/'candidate.sv');(a.out/'reference.sv').write_text(old.read_text().replace('module nes_source_epoch207(','module reference_epoch('),encoding='utf8')
 reset=BASE/'probes/nes-loader217/source02/nes_domain_reset124.sv';shutil.copyfile(reset,a.out/reset.name);pins[str(reset.relative_to(BASE))]=sha(reset)
 # The saved selected207 bench includes real shared reset124, all20 original
 # lifecycle cases, 32 phase/stopped-clock cases, and wrap exhaustion.
 saved=BASE/'probes/nes-board207/epoch02/sim/bench.sv';s=saved.read_text();pins[str(saved.relative_to(BASE))]=sha(saved)
 (a.out/'admission.sv').write_text(s,encoding='utf8')
 bench='''`timescale 1ns/1ps
module diff217;
 reg clk=0,reset=1,begin_load=0;always #3 clk=~clk;
 nes_source_epoch207 dut(.mem_clk(clk),.nes_clk(clk),.reset(reset),.local_reset(reset),.load_begin(begin_load),.load_valid(1'b0),.loaded(1'b0),.run_enable(1'b0),.loader_fault(1'b0),.loaded_bytes(19'd0));
 reference_epoch refdut(.mem_clk(clk),.nes_clk(clk),.reset(reset),.local_reset(reset),.load_begin(begin_load),.load_valid(1'b0),.loaded(1'b0),.run_enable(1'b0),.loader_fault(1'b0),.loaded_bytes(19'd0));
 integer cases=0;reg [31:0] seed=32'h12345678;
 task check;
  @(posedge clk);#0.01;
  if({dut.serial,dut.gray,dut.exhausted}!=={refdut.serial,refdut.gray,refdut.exhausted})$fatal(1,"EPOCH217 diff");
  cases++;
 endtask
 task probe(input [31:0] value);
  @(negedge clk);dut.serial=value;refdut.serial=value;
  // Intentionally inconsistent old Gray verifies next code derives from
  // serial alone, and no-command/overflow preserves even arbitrary old Gray.
  dut.gray=32'h87654321;refdut.gray=32'h87654321;dut.exhausted=0;refdut.exhausted=0;
  begin_load=0;check();@(negedge clk);begin_load=1;check();
  repeat(3)begin @(negedge clk);check();end
 endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;
  for(integer k=0;k<32;k++)begin
   probe((32'b1<<k)-1);probe(32'b1<<k);probe(~((32'b1<<k)-1));
  end
  probe(32'hfffffffe);probe(32'hffffffff);
  for(integer i=0;i<4096;i++)begin
   seed=seed^(seed<<13);seed=seed^(seed>>17);seed=seed^(seed<<5);probe(seed);
  end
  @(negedge clk);reset=1;check();
  @(negedge clk);reset=0;begin_load=1;repeat(4096)begin check();@(negedge clk);end
  $display("PASS EPOCH217 cases=%0d",cases);$finish;
 end
 initial begin #1000000;$fatal(1,"EPOCH217 watchdog");end
endmodule
'''
 (a.out/'diff.sv').write_text(bench,encoding='utf8')
 def run(tool,args,label,negative=None):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert negative in t and 'PASS EPOCH' not in t,t[-2500:]
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-4000:]
  return t
 run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv',reset.name,'admission.sv','diff.sv'],'vlog')
 def sim(top,label,negative=None):return run('vsim',['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f'],label,negative)
 t=sim('diff217','differential');assert 'PASS EPOCH217 cases=25067' in t
 assert 'PASS EPOCH207 baseline=20 cold=32' in sim('source_epoch207_tb','admission')
 wrong=new.read_text().replace('carry_in&!serial[epoch_bit]','carry_in&serial[epoch_bit]');assert wrong!=new.read_text()
 (a.out/'wrong.sv').write_text(wrong,encoding='utf8');run('vlog',['-sv','wrong.sv'],'negative-compile');sim('diff217','negative','** Fatal: EPOCH217 diff')
 r=dict(passed=True,cases=25067,baseline_checks=20,cold_cases=32,wrong_gray_rejected=True,source_pins=pins,script_sha256=sha(Path(__file__)),physical=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
