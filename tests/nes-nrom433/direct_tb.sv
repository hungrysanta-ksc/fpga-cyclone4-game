// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module nrom433_tb;
 reg clk=0,host_clk=0,mem_clk=0,reset=1,run=0,loaded=0,load_begin=0;
 always #22.727 clk=!clk;
 always #5.952 host_clk=!host_clk;
 always #2.976 mem_clk=!mem_clk;
 wire local_reset,source_ready,source_rom,source_write;wire [31:0] epoch;
 nes_domain_reset124 core_release(.clk(clk),.raw_reset(reset||!run),.reset(local_reset));
 nes_source_epoch207 content_lifetime(.mem_clk(mem_clk),.nes_clk(clk),.reset(reset),.local_reset(local_reset),
  .load_begin(load_begin),.load_valid(1'b0),.loaded(loaded),.run_enable(run),.loader_fault(1'b0),.loaded_bytes(loaded?19'h60000:19'd0),
  .source_ready(source_ready),.source_is_rom(source_rom),.source_writing(source_write),.live_epoch(epoch));
 reg capture_begin=0,owned=0,export_release=0;reg [15:0] gen=0;
 wire lease_valid,lease_fault,permitted,export_permitted,drained,retire;wire [31:0] capture_epoch;wire [15:0] captured_gen,retire_gen;
 nes_capture_lease201 lease(.clk(clk),.reset(local_reset),.stop(1'b0),.capture_begin(capture_begin),
 .frame_owned(owned),.geometry_valid(owned),.frame_generation(gen),.export_release(export_release),.export_error(4'd0),
 .source_ready(source_ready),.source_is_rom(source_rom),.source_writing(source_write),.live_epoch(epoch),
 .reader_drained(drained),.retire_commit(retire),.retire_generation(retire_gen),.release_frame(),.lease_valid(lease_valid),
 .retire_permitted(permitted),.export_permitted(export_permitted),.captured_epoch(capture_epoch),.captured_generation(captured_gen),.waiting_display(),.fault(lease_fault));
 `include "spi200_bus.svh"
 wire req,mready,mresponse,merror;wire [21:0] address,ra;wire [7:0] rd;
 reg [23:0] bus_address=0;reg read_n=1,write_n=1;reg [7:0] bus_in=0;
 wire [7:0] bus_data;wire bus_oe,bus_dir,hfault,nfault;
 nes_direct206 dut(.nes_clk(clk),.host_clk(host_clk),.reset(local_reset),.transport_fault(1'b0),
 .lease_valid(lease_valid),.lease_fault(lease_fault),.retire_permitted(permitted),
 .captured_generation(captured_gen),.captured_epoch(capture_epoch),.live_epoch(epoch),
 .source_ready(source_ready),.source_is_rom(source_rom),.source_writing(source_write),.reader_drained(drained),.retire_commit(retire),.retire_generation(retire_gen),
 .core_fault(1'b0),.qualified_slot(1'b1),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),
 .core_ready(),.core_response(),.core_error(),.core_response_address(),.core_data(),
 .mem_ready(mready),.mem_response(mresponse),.mem_error(merror),.mem_response_address(ra),.mem_data(rd),.mem_request(req),.mem_address(address),
 .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.spi_selected(selected197),.spi_miso(miso197),
 .address(bus_address),.read_n(read_n),.write_n(write_n),.data_in(bus_in),.data_out(bus_data),.oe_n(bus_oe),.dir(bus_dir),.host_fault(hfault),.nes_fault(nfault));
 wire [21:0] pa;wire p1,p2,po,pw,ph,pl;wire [15:0] pd;
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem_clk),.reset(local_reset),
 .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),
 .rom_request(req),.rom_address(address),.rom_ready(mready),.rom_response(mresponse),.rom_error(merror),.rom_response_address(ra),.rom_data(rd),
 .psram_address(pa),.psram_1ce(p1),.psram_2ce(p2),.psram_oe(po),.psram_we(pw),.psram_bhe(ph),.psram_ble(pl),.psram_data(pd));
 reg [7:0] memory[0:159];wire [23:0] base={pa,p1,1'b0};
 function automatic [7:0] value(input [23:0] a);
  if(a>=24'h200000&&a<24'h2000a0)value=memory[a-24'h200000];else value=8'hxx;
 endfunction
 assign #70 pd=(!p1^!p2)&&!po&&pw?{ph?8'hzz:value(base),pl?8'hzz:value(base+1)}:16'hzzzz;

 reg [7:0] frame[0:20],expected[0:31],desc[0:11],v;integer reads=0;
 task busread(input [23:0] a,output reg [7:0] out);begin
  @(negedge host_clk);bus_address=a;read_n=0;write_n=1;repeat(8)@(negedge host_clk);
  if(bus_oe||!bus_dir||$isunknown(bus_data))$fatal(1,"invalid bus read %x",a);out=bus_data;read_n=1;repeat(8)@(negedge host_clk);
 end endtask
 task buswrite(input [23:0] a,input [7:0] value);begin
  @(negedge host_clk);bus_address=a;bus_in=value;write_n=0;read_n=1;repeat(8)@(negedge host_clk);write_n=1;repeat(8)@(negedge host_clk);
 end endtask
 initial begin
  $readmemh("frame.mem",memory,0,159);$readmemh("frame.expected",expected,0,31);$readmemh("batch.hex",frame,0,20);
  repeat(5)@(negedge clk);reset=0;@(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;loaded=1;run=1;
  wait(source_ready);repeat(10)@(negedge clk);@(negedge clk);gen=3;capture_begin=1;@(negedge clk);capture_begin=0;gen=4;owned=1;
  @(negedge clk);export_release=1;@(negedge clk);export_release=0;owned=0;wait(lease_valid);
  status197();if(!rx197[3][0])$fatal(1,"no plan credit");
  begin197();for(integer i=0;i<21;i++)byte197(frame[i],v);end197();
  for(integer chunk=0;chunk<1;chunk++)begin
   wait(dut.chunk_ready || hfault || nfault);if(hfault||nfault)$fatal(1,"tile path fault");
   status197();if(rx197[6]!=1)$fatal(1,"descriptor status");
   for(integer i=0;i<12;i++)busread(24'h006040+i,desc[i]);
   $display("DIAG descriptor chunk=%0d ready=%h kind=%h length=%0d offset=%0d gen=%0d token=%h%h%h%h",chunk,desc[0],desc[1],{desc[3],desc[2]},{desc[5],desc[4]},{desc[7],desc[6]},desc[11],desc[10],desc[9],desc[8]);
   if(desc[0]!=1||desc[1]!=0||{desc[3],desc[2]}!=32||{desc[7],desc[6]}!=4||{desc[5],desc[4]}!=chunk*16)$fatal(1,"descriptor mismatch");
   for(integer i=0;i<32;i++)begin busread(24'h400800+i,v);if(v!==expected[i])$fatal(1,"tile byte mismatch chunk=%0d byte=%0d got=%h expected=%h",chunk,i,v,expected[i]);reads++;end
   $display("DIAG read complete reads=%0d",reads);for(integer i=0;i<4;i++)buswrite(24'h00604c+i,desc[8+i]);buswrite(24'h006050,8'ha5);$display("DIAG consume fault=%b ready=%b",hfault,dut.chunk_ready);wait(!dut.chunk_ready);$display("DIAG consumed");
  end
   $display("DIAG poll end");status197();
  for(integer k=0;k<100 && rx197[3]!=2;k++)begin if(hfault||nfault)$fatal(1,"end fault");status197();end
  if(rx197[3]!=2)$fatal(1,"not end status %h",rx197[3]);
  begin : retire_request
   reg [7:0] c;c=0;begin197();byte197(8'hea,v);c=crc8_197(c,8'hea);byte197(8'h04,v);c=crc8_197(c,8'h04);byte197(0,v);c=crc8_197(c,0);byte197(0,v);c=crc8_197(c,0);byte197(1,v);c=crc8_197(c,1);byte197(c,v);byte197(8'ha5,v);end197();
  end
  wait(!lease_valid);wait(drained);if(hfault||nfault)$fatal(1,"retire fault");
  run=0;wait(local_reset);repeat(10)@(negedge host_clk);if(lease_valid||!bus_oe)$fatal(1,"STOP exposed data");
  $display("PASS NROM433 E9 plan SPI tile SNES read/consume END lease retire STOP bytes=%0d",reads);$finish;
 end
 initial begin #5000000;$fatal(1,"NROM433 watchdog");end
endmodule
