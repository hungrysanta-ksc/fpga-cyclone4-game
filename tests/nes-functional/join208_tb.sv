// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module join208_tb;
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
 import "DPI-C" function int join208_poll();
 import "DPI-C" function int join208_get(input int i);
 import "DPI-C" function void join208_put(input int i,input int v);
 import "DPI-C" function void join208_reply(input int n);
 integer op,n,a,frames=0,retires=0,reads=0,writes=0,commands=0;reg [7:0] v;
 always @(posedge clk)if(retire)retires<=retires+1;
 initial begin
  repeat(5)@(negedge clk);reset=0;
  forever begin
   op=join208_poll();n=join208_get(4)+256*join208_get(5);a=join208_get(1)+256*join208_get(2)+65536*join208_get(3);
   case(op)
    0:repeat(10)@(negedge host_clk);
    1:begin
     begin197();for(integer i=0;i<n;i++)begin byte197(8'(join208_get(8+i)),v);join208_put(i,int'(v));end end197();join208_reply(n);
    end
    2:begin
     for(integer i=0;i<n;i++)begin
      @(negedge host_clk);bus_address=24'(a+i);read_n=0;write_n=1;
      repeat(8)@(negedge host_clk);if(bus_oe||!bus_dir||$isunknown(bus_data))$fatal(1,"invalid bus read %x",bus_address);
      join208_put(i,int'(bus_data));read_n=1;repeat(8)@(negedge host_clk);reads++;
     end
     join208_reply(n);
    end
    3:begin
     for(integer i=0;i<n;i++)begin
      @(negedge host_clk);bus_address=24'(a+i);bus_in=8'(join208_get(8+i));write_n=0;read_n=1;
      repeat(8)@(negedge host_clk);write_n=1;repeat(8)@(negedge host_clk);writes++;
     end
     join208_reply(0);
    end
    4:begin
     if(frames!=retires||lease_valid||n!=162)$fatal(1,"early next frame");
     for(integer i=0;i<160;i++)begin
      if(frames>0&&memory[i]!==8'(join208_get(i+10)))$fatal(1,"unversioned ROM mutation");memory[i]=8'(join208_get(i+10));
     end
     if(frames==0)begin
      @(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;loaded=1;run=1;wait(source_ready);repeat(10)@(negedge clk);
     end
     @(negedge clk);gen=16'(join208_get(8)+256*join208_get(9))-1'b1;capture_begin=1;
     @(negedge clk);capture_begin=0;gen=gen+1'b1;owned=1;frames++;join208_reply(0);
    end
    5:begin
     @(negedge clk);if(!export_permitted)$fatal(1,"export denied");export_release=1;
     @(negedge clk);export_release=0;owned=0;repeat(10)@(negedge clk);if(!lease_valid)$fatal(1,"no exported lease");join208_reply(0);
    end
    6:begin
     repeat(30)@(negedge host_clk);if(!hfault&&!nfault)$fatal(1,"partial SPI not rejected");
     run=0;repeat(30)@(negedge host_clk);if(lease_valid||dut.chunk_ready||!bus_oe)$fatal(1,"canceled data exposed");join208_reply(0);
    end
    9:begin
     // fill_idle/drained is intentionally false while common reset is held.
     if(lease_valid||(!local_reset&&(!drained||hfault||nfault)))$fatal(1,"not retired");join208_reply(0);
     $display("PASS JOIN208 RTL frames=%0d retires=%0d reads=%0d writes=%0d SPI=%0d",frames,retires,reads,writes,spi_calls197);$finish;
    end
    default:$fatal(1,"bridge timeout/command %0d",op);
   endcase
   if(op)commands++;
  end
 end
endmodule
