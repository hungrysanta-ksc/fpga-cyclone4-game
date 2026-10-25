# SPDX-License-Identifier: MIT
"""Actual shared SPI/retire/EA/source cache/arbiter/READ16 guard integration."""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import BASE,sha
from probe_nes_refill267 import run
TB=r'''
`timescale 1ns/1ps
module guard361_tb;
 reg h=0,n=0;always #5.952380952 h=~h;always #22.727272727 n=~n;
 reg reset=1,stop=0,ss=1,sck=0,mosi=0,pre=1,displaylease=0,immutable=1,ended=0;
 wire [113:0] link;wire [199:0] status;wire take,selected,miso,pfault,retire,active,request,hfault,busy,finished;
 wire pw,seal;wire [21:0] address;wire [7:0] pd;wire [9:0] plen;wire [4:0] pcount;wire [15:0] pcrc;
 wire response,ready,error;integer reads=0,retired=0,seals=0,finishes=0,stopbyte=-1;
 nes_spi270 front(.clk(h),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.source_status(200'd0),.output_status(200'd0),.plan_status(status),.request_crc_enable(take),.queue_admit319(1'b1),.plan_admit319(1'b1),.link(link));
 nes_plan_spi200 ep(.clk(h),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(1'b0),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.link270(link),.status270(status),.crc_take270(take),.selected(selected),.miso(miso),.fault(pfault),.plan_idle(1'b1),.plan_ready(1'b1),.plan_write(pw),.plan_data(pd),.plan_seal(seal),.plan_length(plen),.plan_plans(pcount),.plan_crc(pcrc),.retire_done(1'b0),.retire(retire),.end_generation(16'd3),.chunk_ready(1'b0),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),.chunk_generation(16'd0),.chunk_token(32'd0),.end_sealed(ended));
 nes_hint361 hint(h,n,reset,stop,pre,displaylease,immutable,16'd3,32'd1,32'd3,link,active,request,address,ready,response,error,hfault,busy,finished);
 reg mc=0;always #2.976190476 mc=~mc;
 wire mr,mready,mresponse,merror;wire [21:0] ma,mra,ps;wire [7:0] md;wire [15:0] pdrom;
 wire c1,c2,oe,we,bhe,ble,drained,sourcefault;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) source(.clk(n),.reset(reset),.stop(stop),.frame_owned(displaylease),.geometry_valid(displaylease),.frame_generation(16'd3),
 .source_ready(1'b1),.source_is_rom(immutable),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1),
 .hint_active361(active),.hint_request361(request),.hint_owner361(pre),.hint_address361(address),.hint_ready361(ready),.hint_response361(response),.hint_error361(error),
 .plan_valid(1'b0),.plan_kind(2'd0),.plan_generation(16'd3),.plan_slot(10'd1),.plan_tag(13'd6525),.plan_rows(48'hff6b646d2240),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
 .qualified_slot(1'b1),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),.out_ready(1'b1),
 .mem_ready(mready),.mem_response(mresponse),.mem_error(merror),.mem_response_address(mra),.mem_data(md),.mem_request(mr),.mem_address(ma),.drained(drained),.fault(sourcefault));
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(n),.mem_clk(mc),.reset(reset),.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),
 .rom_request(mr),.rom_address(ma),.rom_ready(mready),.rom_response(mresponse),.rom_error(merror),.rom_response_address(mra),.rom_data(md),
 .psram_address(ps),.psram_1ce(c1),.psram_2ce(c2),.psram_oe(oe),.psram_we(we),.psram_bhe(bhe),.psram_ble(ble),.psram_data(pdrom));
 wire [23:0] pa={ps,c1,1'b0};
 function automatic [7:0] value(input [23:0] a);return a[7:0]^a[15:8]^a[23:16];endfunction
 assign #70 pdrom=(!c1 ^ !c2)&&!oe&&we?{bhe?8'hzz:value(pa),ble?8'hzz:value(pa+1)}:16'hzzzz;
 always @(posedge n)begin
  if(!reset&&request&&ready)reads++;
  if(finished)finishes++;
  if(response&&(error||source.cache_path.cache.response_address!==address||source.cache_path.cache.data!==value(address)))$fatal(1,"hint ROM response");
 end
 always @(posedge h)begin if(retire)retired++;if(seal)seals++;end
 reg [7:0] packet[0:31],gold[0:23];integer cases=0;reg [15:0] c16v;reg [7:0] c8v;
 function automatic [15:0] c16(input [15:0] a,input [7:0] b);reg [15:0] c;begin c=a^{b,8'd0};for(integer j=0;j<8;j++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;end endfunction
 function automatic [7:0] c8(input [7:0] a,input [7:0] b);reg [7:0] c;begin c=a^b;for(integer j=0;j<8;j++)c=c[7]?(c<<1)^8'h07:c<<1;return c;end endfunction
 task setup;begin reset=1;stop=0;pre=1;displaylease=0;immutable=1;ended=0;ss=1;sck=0;#1000;reset=0;#1000;reads=0;retired=0;seals=0;finishes=0;for(integer j=0;j<24;j++)packet[j]=gold[j];end endtask
 task send(input integer size);begin ss=0;#2000;for(integer j=0;j<size;j++)begin
  for(integer k=7;k>=0;k--)begin mosi=packet[j][k];#190.476190476;sck=1;#190.476190476;sck=0;end
  if(j==stopbyte)begin stop=1;#1000;stop=0;#1000;end
 end #2000;ss=1;#8000;end endtask
 task crcfix;begin c16v=16'hffff;for(integer j=0;j<22;j++)c16v=c16(c16v,packet[j]);packet[22]=c16v[7:0];packet[23]=c16v[15:8];end endtask
 initial begin
  $readmemh("hint361.hex",gold);
  setup();send(24);#200000;if(reads!=80||finishes!=1||pfault||hfault||retired||seals)$fatal(1,"normal hint reads=%0d finishes=%0d pf=%0d hf=%0d",reads,finishes,pfault,hfault);cases++;
  send(24);if(!hfault||reads!=80||retired)$fatal(1,"duplicate");cases++;
  for(integer cut=1;cut<24;cut++)begin setup();send(cut);#2000;if(reads||retired||seals)$fatal(1,"truncated %0d",cut);cases++;end
  setup();packet[24]=0;send(25);if(reads||retired||!pfault)$fatal(1,"long packet");cases++;
  for(integer bad=0;bad<8;bad++)begin
   setup();case(bad)
    0:packet[22]^=1;
    1:begin packet[2]^=1;crcfix();end
    2:begin packet[4]^=1;crcfix();end
    3:begin packet[8]^=1;crcfix();end
    4:begin packet[13]|=8'he0;crcfix();end
    5:immutable=0;6:pre=0;7:displaylease=1;
   endcase
   #1000;send(24);if(reads||retired||(!pfault&&!hfault))$fatal(1,"bad admission %0d",bad);cases++;
  end
  setup();send(24);wait(source.cache_path.cache.pending);@(negedge n);stop=1;wait(drained);#5000;if(active||request||finished||retired)$fatal(1,"STOP pending");
  for(integer j=0;j<5;j++)if(source.cache_path.cache.valid[j]!=0)$fatal(1,"STOP cache validity");
  stop=0;#5000;if(active||request||finished||retired||finishes)$fatal(1,"DONE after STOP release");cases++;
  for(integer k=0;k<24;k++)begin setup();stopbyte=k;send(24);if(active||reads||retired||finishes)$fatal(1,"STOP wire tail %0d",k);cases++;end
  stopbyte=-1;
  // Existing EA seven-byte retire remains accepted only after end seal.
  setup();pre=0;displaylease=1;@(negedge h);ended=1;@(negedge h);ended=0;
  packet[0]=8'hea;packet[1]=3;packet[2]=0;packet[3]=0;packet[4]=0;c8v=0;for(integer j=0;j<5;j++)c8v=c8(c8v,packet[j]);packet[5]=c8v;packet[6]=8'ha5;send(7);
  if(retired!=1||pfault||hfault||reads)$fatal(1,"legacy retire retired=%0d pf=%0d hf=%0d reads=%0d",retired,pfault,hfault,reads);cases++;
  $display("PASS GUARD361 cases=%0d",cases);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 names=['nes_spi270.sv','nes_plan_spi200.sv','nes_domain_reset124.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile205.sv','nes_native_arbiter165.sv','nes_rom_physical.sv']
 for n in names+['hint361.hex']:shutil.copyfile(a.source/n,d/n)
 s=(a.source/'nes_plan_rom267.sv').read_text();(d/'nes_hint361.sv').write_text(s[s.index('module nes_hint361'):]);names+=['nes_hint361.sv']
 (d/'guard361_tb.sv').write_text(TB,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*names,'guard361_tb.sv'],d,'vlog')
 raw=run(q/'vsim.exe',['-c','work.guard361_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120);assert 'PASS GUARD361' in raw
 r=dict(passed=True,pins={str(d/n):sha(d/n) for n in names+['guard361_tb.sv','hint361.hex']},scope=__doc__)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(raw[-500:])
if __name__=='__main__':main()
