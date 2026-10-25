# SPDX-License-Identifier: MIT
"""Exhaust the source cursor/raw-mode query selector before removing query6."""
import argparse,json,re,shutil
from pathlib import Path
from nes_delta231 import ROOT,sha
from probe_nes_refill267 import run
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 source=ROOT/'src/fpga/nes_hint367/nes_core257.sv';shutil.copyfile(source,d/source.name)
 header=source.read_text().split('module nes_core257(',1)[1].split(');',1)[0];ports=[];direction=None
 values=dict(clk='clk',reset="1'b1",query_kind='query_kind')
 for part in header.split(','):
  part=part.strip();m=re.match(r'(input|output)\s+(?:wire|reg)\s+',part)
  if m:direction=m[1];part=part[m.end():]
  name=re.sub(r'^\[[^]]+\]\s*','',part);assert re.fullmatch(r'\w+',name),name
  ports.append(f'.{name}({values.get(name,"\'0" if direction=="input" else "")})')
 tb='''`timescale 1ns/1ps
module query368_tb;
 reg clk=0;always #5 clk=~clk;
 reg [12:0] cursor368=0;reg raw368=0;wire [2:0] query_kind;
 nes_core257 dut(PORTS);
 initial begin
  force dut.q_cursor=cursor368;force dut.raw_mode=raw368;
  #100;
  for(integer mode368=0;mode368<2;mode368++)begin raw368=mode368;
   for(integer i=0;i<8192;i++)begin cursor368=i;#1;
    if($isunknown(query_kind)||query_kind==6)$fatal(1,"unexpected source query6/unknown mode%0d cursor%0d kind%0d",mode368,i,query_kind);
   end
  end
  $display("PASS QUERY368 selectors=16384");$finish;
 end
endmodule
'''.replace('PORTS',','.join(ports))
 (d/'query368_tb.sv').write_text(tb,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_core257.sv','query368_tb.sv'],d,'vlog')
 log=run(q/'vsim.exe',['-c','work.query368_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',180);assert 'PASS QUERY368 selectors=16384' in log
 result=dict(passed=True,selectors=16384,pins={p.name:sha(p) for p in d.glob('*.sv')});(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(log[-500:])
if __name__=='__main__':main()
