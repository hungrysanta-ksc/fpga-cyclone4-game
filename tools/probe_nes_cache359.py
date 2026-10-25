# SPDX-License-Identifier: MIT
"""Actual 272B cache/arbiter/READ16 reader; packet serialization is a TB driver.

This is a lower-bound port experiment, not an integrated EA dispatcher, lease,
SPI arbitration or ARM IRQ run. It cannot establish a full-frame speedup.
"""
import argparse,json,re,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
from nes_cache359 import apply
from probe_nes_refill267 import run

TB=r'''
`timescale 1ns/1ps
module cache359_tb;
 parameter integer PHASE=5677152;
 reg clk=0,mc=0;always #22.727272727 clk=~clk;always #2.976190476 mc=~mc;
 reg reset=1,flush=0,request=0;reg [21:0] address=0;
 reg [31:0] epoch=1;reg [15:0] generation=1;
 wire ready,idle,response,error;wire [21:0] ra;wire [15:0] rg;wire [7:0] data;
 wire br,ba,bready,bidle,bresponse,berror;wire [21:0] bad,brr;wire [15:0] bg,brg;wire [7:0] bd;
 wire mr,mready,mresponse,merror;wire [21:0] ma,mra;wire [7:0] md;
 wire cr,cv,ce;wire [21:0] cra;wire [7:0] cd;wire fault;
 wire [21:0] ps;wire c1,c2,oe,we,bhe,ble;wire [15:0] pd;
 integer cycle=PHASE,reads=0,core_reads=0;
 wire qualified=(cycle%357368>=330088&&cycle%357368<354640&&cycle%12==3);
 wire core_request=cr&&cycle%120==3;
 nes_chr_cache192 cache(clk,reset,flush,request,epoch,address,generation,ready,idle,response,error,ra,rg,data,br,ba,bad,bg,bready,bidle,bresponse,berror,brr,brg,bd);
 nes_native_arbiter165 arb(clk,reset,qualified,1'b1,core_request,22'h1234,cr,cv,ce,cra,cd,br,ba,bad,bg,bready,bidle,bresponse,berror,brr,brg,bd,mready,mresponse,merror,mra,md,mr,ma,fault);
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mc),.reset(reset),.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),
 .check_ready(),.check_response(),.check_response_address(),.check_data(),.rom_request(mr),.rom_address(ma),.rom_ready(mready),.rom_response(mresponse),.rom_error(merror),.rom_response_address(mra),.rom_data(md),
 .psram_address(ps),.psram_1ce(c1),.psram_2ce(c2),.psram_oe(oe),.psram_we(we),.psram_bhe(bhe),.psram_ble(ble),.psram_data(pd));
 function automatic [7:0] value(input [23:0] a);value=a[7:0]^a[15:8]^a[23:16];endfunction
 wire [23:0] pa={ps,c1,1'b0};
 assign #70 pd=(!c1 ^ !c2)&&!oe&&we?{bhe?8'hzz:value(pa),ble?8'hzz:value(pa+1)}:16'hzzzz;
 always @(posedge clk)if(!reset)begin
  cycle++;
  if(fault)$fatal(1,"arbiter fault");
  if(mr&&mready&&ma!=22'h1234)begin reads++;if(!qualified||core_request)$fatal(1,"unsafe ROM grant");end
  if(cv)begin core_reads++;if(ce||cd!==8'h26)$fatal(1,"core response");end
 end
 reg [7:0] packet[0:47];reg ss=1,sck=0,mosi=0;integer spi_bytes=0;reg [7:0] wire_byte=0;integer bit_at=0;
 // A pin serializer/capture fixture, NOT a synthesized/validated EA receiver.
 always @(posedge sck)if(!ss)begin
  wire_byte={wire_byte[6:0],mosi};bit_at++;
  if(bit_at==8)begin if(wire_byte!==packet[spi_bytes])$fatal(1,"SPI packet");spi_bytes++;bit_at=0;end
 end
 task get(input integer a);
 begin
  @(negedge clk);address=a;request=1;
  do @(posedge clk);while(!ready);
  @(negedge clk);request=0;
  wait(response);if(error||ra!==address||rg!==generation||data!==value(address))$fatal(1,"cache response");
  @(negedge clk);
 end endtask
 integer before_reads;realtime started,wire_end,filled;
 initial begin
  $readmemh("packet.hex",packet);repeat(4)@(negedge clk);reset=0;started=$realtime;
  // Actual ARM firstpacket delay at CPI1/84MHz; prefix+extra tracking+filter.
  #1743677.381;
  ss=0;
  for(integer j=0;j<48;j++)for(integer k=7;k>=0;k--)begin mosi=packet[j][k];#190.476190476;sck=1;#190.476190476;sck=0;end
  ss=1;#8000;wire_end=$realtime;
  for(integer j=0;j<17;j++)for(integer k=0;k<16;k++)get(22'h200000+({packet[13+2*j],packet[12+2*j]}*16)+k);
  filled=$realtime;
  if(reads!=272)$fatal(1,"fill count");before_reads=reads;
  for(integer j=0;j<17;j++)for(integer k=0;k<16;k++)get(22'h200000+({packet[13+2*j],packet[12+2*j]}*16)+k);
  if(reads!=before_reads)$fatal(1,"cache did not retain 272 bytes");
  $display("COST359 phase=%0d SPI=%0d ROM=%0d core=%0d wire_ns=%0f fill_ns=%0f",PHASE,spi_bytes,reads,core_reads,wire_end-started,filled-started);
  // STOP an accepted physical fill, drain, then prohibit stale cache exposure.
  fork
   begin get(22'h21fff0);$fatal(1,"STOP response escaped");end
   begin wait(cache.pending);@(negedge clk);flush=1;request=0;wait(bidle);repeat(8)@(negedge clk);end
  join_any
  disable fork;
  if(response||cache.pending)$fatal(1,"STOP not drained");
  for(integer j=0;j<17;j++)if(cache.valid[j]!=0)$fatal(1,"STOP valid leak");
  flush=0;epoch=2;repeat(3)@(negedge clk);
  before_reads=reads;get(22'h200000+({packet[13],packet[12]}*16));
  if(reads!=before_reads+1)$fatal(1,"epoch reused old bytes");
  $display("PASS CACHE359 retention STOP drain epoch");$finish;
 end
 initial begin #80000000;$fatal(1,"timeout359");end
endmodule
'''

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 ref=BASE/'probes/nes-raster355/fixed01';names=['nes_chr_cache192.sv','nes_native_arbiter165.sv','nes_rom_physical.sv']
 pins={}
 for n in names:shutil.copyfile(ref/n,d/n);pins[str(ref/n)]=sha(ref/n)
 apply(d);(d/'cache359_tb.sv').write_text(TB,newline='\n')
 packet=BASE/'probes/nes-prefetch359/arm02/prefetch907.bin';pins[str(packet)]=sha(packet)
 (d/'packet.hex').write_text(''.join(f'{b:02x}\n' for b in packet.read_bytes()),newline='\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'cache359_tb.sv'],d,'vlog');rows=[]
 for phase in (5677152,7368026):
  raw=run(q/'vsim.exe',['-c','work.cache359_tb',f'-gPHASE={phase}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'phase{phase}',240)
  assert 'PASS CACHE359' in raw
  row=re.search(r'COST359 phase=(\d+) SPI=(\d+) ROM=(\d+) core=(\d+) wire_ns=([\d.]+) fill_ns=([\d.]+)',raw);assert row
  rows.append(dict(zip(('phase','SPI_bytes','ROM_bytes','core_reads','wire_ns','fill_ns'),map(float,row.groups()))))
 for n in [*names,'cache359_tb.sv']:pins[str(d/n)]=sha(d/n)
 result=dict(passed=True,rows=rows,pins=pins,scope=__doc__,integrated_dispatch=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
