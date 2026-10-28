# SPDX-License-Identifier: MIT
"""Expose the fixed-register prototype's missing unpublished-header gate.
This is a rejection counterexample, not an additional passing guard for it.
"""
import argparse,json,re,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.out.resolve();root.mkdir(parents=True,exist_ok=False);cases=[]
 for label,unit,expected in(('fixed_host','host02',1),('funded_RAM','host03',0)):
  ref=BASE/'probes/nes-joint402'/unit;d=root/label;d.mkdir();r=json.loads((ref/'result.json').read_text());sources=list(r['RTL'])
  for n in sources:shutil.copyfile(ref/n,d/n)
  if(ref/'program398.hex').exists():shutil.copyfile(ref/'program398.hex',d/'program398.hex')
  s=(d/'nes_mux260.sv').read_text();head=s[s.index('output wire',s.index('module ')):s.index(');',s.index('module '))];direction=None;ports=[]
  values=dict(host_clk='clk',nes_clk='clk',reset='reset',init278="1'b1",SPI_SS="1'b1",read_n='read_n',write_n='write_n',address='address',data_in='data_in',bus_valid='bus_valid',fault='fault')
  for part in head.split(','):
   part=part.strip();m=re.match(r'(input|output)\s+(?:wire|reg)\s*',part)
   if m:direction=m[1];part=part[m.end():]
   name=re.sub(r'^\[[^]]+\]\s*','',part);assert re.fullmatch(r'\w+',name),name
   ports.append('.'+name+'('+values.get(name,"'0"if direction=='input'else'')+')')
  tb='''`timescale 1ns/1ps
module header402_tb;
 reg clk=0;always #6 clk=~clk;
 reg reset=1,read_n=1,write_n=1;reg[23:0]address=0;reg[7:0]data_in=0;wire bus_valid,fault;
 nes_output260 dut(PORTS);
 initial begin
  repeat(10)@(negedge clk);reset=0;repeat(100)@(negedge clk);
  address=24'h006006;data_in=8'ha5;write_n=0;#200;write_n=1;#200;
  if(fault||dut.invalidate_banks)$fatal(1,"invalid startup in header402");
  address=24'h006080;read_n=0;#200;
  if(dut.staged||bus_valid!==1'bEXPECTED)$fatal(1,"unexpected header publication state");
  $display("HEADER402 unpublished_valid=%0d",bus_valid);$finish;
 end
 initial begin #100000;$fatal(1,"header402 timeout");end
endmodule
'''.replace('PORTS',','.join(ports)).replace('EXPECTED',str(expected))
  (d/'header402_tb.sv').write_text(tb,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
  run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*sources,'header402_tb.sv'],d,'vlog')
  log=run(q/'vsim.exe',['-c','work.header402_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120);assert f'HEADER402 unpublished_valid={expected}'in log
  cases.append(dict(variant=label,unpublished_header_accessible=bool(expected),contract_passed=not expected,RTL=r['RTL'],test=sha(d/'header402_tb.sv')))
 (root/'result.json').write_text(json.dumps(dict(audit_passed=True,cases=cases,scope=__doc__),indent=2)+'\n',newline='\n');print(json.dumps(cases))
if __name__=='__main__':main()
