# SPDX-License-Identifier: MIT
"""Real SPI command ownership of the existing MCU_RDY pin, including held CS."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import sha
from probe_nes_refill267 import run
TB=r'''
`timescale 1ns/1ps
module irq367_tb;
 reg clk=0;always #5.952380952 clk=~clk;
 reg reset=1,ss=1,sck=0,mosi=0,source_ready=0,external_ready=1;
 wire source_mode,progress_mode,progress_irq;wire [113:0] link;
 wire gpio=source_mode?source_ready:progress_mode?progress_irq:external_ready;
 nes_spi270 spi(.clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
  .source_status({199'd0,source_ready}),.output_status(200'd0),.plan_status(200'd0),
  .progress_irq284(progress_irq),.progress_mode284(progress_mode),.source_mode367(source_mode),
  .request_crc_enable(1'b0),.queue_admit319(1'b1),.plan_admit319(1'b1),.link(link));
 task byte_spi(input [7:0] b);begin for(integer k=7;k>=0;k--)begin
  mosi=b[k];#190.476190476;sck=1;#190.476190476;sck=0;
 end #100;end endtask
 task command(input [7:0] b);begin ss=0;#2000;byte_spi(b);ss=1;#2000;end endtask
 integer cases=0;
 initial begin
  #1000;reset=0;#2000;if(!gpio||source_mode||progress_mode)$fatal(1,"reset owner");cases++;
  command(8'hd4);if(!source_mode||gpio||progress_mode)$fatal(1,"empty source must sleep despite external ready");cases++;
  source_ready=1;#100;if(!gpio)$fatal(1,"source wake");cases++;
  command(8'hea);if(!source_mode||!gpio)$fatal(1,"hint lost source pin ownership");cases++;
  source_ready=0;#100;if(gpio)$fatal(1,"source deassertion");cases++;
  // Prefix and payload are separated by ARM execution while CS stays low.
  ss=0;#2000;byte_spi(8'hd4);repeat(12)byte_spi(0);#20000;
  if(!source_mode||gpio)$fatal(1,"held prefix owner");cases++;
  repeat(250)byte_spi(0);ss=1;#2000;
  command(8'he2);if(source_mode||!progress_mode)$fatal(1,"output progress owner");cases++;
  command(8'hea);if(source_mode||!progress_mode)$fatal(1,"retire keeps progress owner");cases++;
  command(8'hd5);if(!source_mode||progress_mode)$fatal(1,"input ACK owner");cases++;
  command(8'he8);if(source_mode||!progress_mode)$fatal(1,"output IRQ arm owner");cases++;
  reset=1;#100;if(source_mode||progress_mode)$fatal(1,"STOP/reset stale owner");cases++;
  $display("PASS IRQ367 cases=%0d",cases);$finish;
 end
 initial begin #5000000;$fatal(1,"timeout");end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(a.source/'nes_spi270.sv',d/'nes_spi270.sv');(d/'irq367_tb.sv').write_text(TB,newline='\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_spi270.sv','irq367_tb.sv'],d,'vlog')
 log=run(q/'vsim.exe',['-c','work.irq367_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120)
 assert 'PASS IRQ367 cases=11' in log
 result=dict(passed=True,cases=11,pins={n:sha(d/n) for n in ('nes_spi270.sv','irq367_tb.sv')})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(log[-500:])
if __name__=='__main__':main()
