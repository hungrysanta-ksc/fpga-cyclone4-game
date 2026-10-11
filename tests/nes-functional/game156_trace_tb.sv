// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module trace156_tb;
 parameter real HALF_CLOCK=5;
 parameter integer SCK_HALF=100;
 reg clk=0,host=0,reset=1,core_reset=1,commit=0,strobe=0,read_clock=0;
 always #(HALF_CLOCK) clk=~clk;always #7 host=~host;
 reg [15:0] snes_buttons=0;wire serial,old_serial,ready,old_ready,event_valid;wire [7:0] buttons;
 nes_game_pad150 pad(host,clk,core_reset,commit,snes_buttons,ready,strobe,read_clock,serial,event_valid,buttons);
 nes_game_pad155 original(host,clk,core_reset,commit,snes_buttons,old_ready,strobe,read_clock,old_serial);
 reg ss=1,sck=0,mosi=0,fault=0;wire selected,miso;
 nes_run_observer134 observer(.clk(clk),.reset(reset),.core_reset(core_reset),.cpu_sample(1'b0),.rom_fault(fault),
 .rom_error(4'd2),.ppu_fault_state154(64'h123456789abcdef0),.fault_trigger(fault),.fault_context(64'hfedcba9876543210),
 .pad_event(event_valid),.pad_buttons(buttons),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso));
 integer events=0;reg [7:0] latest;
 always @(posedge clk)if(!core_reset)begin
  if(serial!==old_serial || ready!==old_ready)$fatal(1,"pad behavior changed");
  if(event_valid)begin events=events+1;latest=buttons;end
 end
 task poll(input [7:0] value,input integer bits);
  integer i,before_count;begin
   wait(ready);@(negedge host);
   snes_buttons=0;snes_buttons[7]=value[0];snes_buttons[15]=value[1];snes_buttons[13:8]={value[2],value[3],value[4],value[5],value[6],value[7]};
   commit=1;@(negedge host);commit=0;repeat(10)@(negedge clk);
   strobe=1;repeat(3)@(negedge clk);strobe=0;before_count=events;
   for(i=0;i<bits;i=i+1)begin read_clock=1;repeat(3)@(negedge clk);read_clock=0;repeat(3)@(negedge clk);end
   repeat(3)@(negedge clk);
   if(bits>=8)begin if(events!=before_count+1||latest!==value)$fatal(1,"completed read %h/%h",value,latest);end
   else if(events!=before_count)$fatal(1,"partial read recorded");
  end
 endtask
 reg [55:0] page;reg [7:0] b;integer i,j;reg [55:0] saved;
 task spi(input [7:0] cmd);
  integer x,y;reg [7:0] tx,rx;begin
   ss=0;#150;page=0;
   for(x=0;x<8;x=x+1)begin tx=x==0?cmd:0;rx=0;
    for(y=7;y>=0;y=y-1)begin mosi=tx[y];#(SCK_HALF);sck=1;#(SCK_HALF);rx[y]=miso;sck=0;end
    if(x>0)page={page[47:0],rx};
   end
   ss=1;#150;
  end
 endtask
 initial begin
  #100;reset=0;core_reset=0;#100;
  poll(0,8);poll(8,8);poll(8,8);poll(0,8);poll(4,8);poll(0,3);
  spi(8'h76);if(page[47:40]!=0||page[39:24]!=4||page[23:16]!=4)$fatal(1,"header before stop %h",page);
  for(i=0;i<256;i=i+1)poll(i[7:0],10);
  spi(8'h76);if(page[39:24]!=260||page[23:16]!=16||page[15:8]!=4)$fatal(1,"ring %h",page);
  spi(8'h84);if(page[55:48]!=8'hdf||page[47:40]!=240||page[15:8]!=0||page[7:0]!=1)$fatal(1,"oldest/quantum %h",page);
  @(negedge clk);fault=1;repeat(2)@(negedge clk);fault=0;core_reset=1;repeat(3)@(negedge clk);
  spi(8'h76);if(page[47:40]!=1)$fatal(1,"freeze %h",page);saved=page;
  core_reset=0;#100;poll(8,8);spi(8'h76);if(page!==saved)$fatal(1,"lost after STOP");
  spi(8'h71);if(page[55:48]!=8'hdf||page[47:40]!=1||page[39:0]!=40'hfedcba9876)$fatal(1,"old context page %h",page);
  $display("PASS156 trace all256 masks,partial/overread,duplicate,ring260,last16,STOP retention,old context SPI");$finish;
 end
 initial begin #10000000;$fatal(1,"watchdog");end
endmodule
