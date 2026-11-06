// SPDX-License-Identifier: MIT
// A second, separate experiment at the boot observer, upstream of plan traffic.
`timescale 1ns/1ps
module boot641_tb;
 reg host=0, reset=1, active=0, rd_n=1, wr_n=1, romsel_n=1;
 reg [23:0] addr=0;
 reg [7:0] din=0;
 always #5.952 host=!host;
 `include "spi200_bus.svh"
 nes_screen_status151 observer(.clk(host),.reset(reset),.active(active),.address(addr),
  .read_n(rd_n),.write_n(wr_n),.romsel_n(romsel_n),.data_in(din),.bus_drive(1'b0),
  .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.receive_write(),
  .selected(selected197),.miso(miso197));
 reg [7:0] accumulated;
 task vector_reads;
  @(negedge host);rd_n=0;romsel_n=0;addr='hfffc;repeat(8)@(negedge host);
  addr='hfffd;repeat(8)@(negedge host);rd_n=1;romsel_n=1;
 endtask
 task spi73(input [7:0] stage,input [7:0] expected);
  begin197();byte197('h73,rx197[0]);for(int i=1;i<8;i++)byte197(0,rx197[i]);end197();
  accumulated=accumulated|rx197[4]; // screen146 combines pin samples across polls.
  if(rx197[1]!=='he6 || rx197[2]!==stage || rx197[3]!==0 || rx197[7]!==3 ||
     accumulated!==expected)$fatal(1,"73 stage=%h flags=%h",rx197[2],accumulated);
 endtask
 task boot_case(input integer which);
  reset=1;active=0;rd_n=1;wr_n=1;romsel_n=1;addr=0;accumulated=0;
  repeat(8)@(negedge host);reset=0;
  if(which==1)vector_reads(); // Completed before observer active.
  @(negedge host);active=1;
  if(which==2)vector_reads(); // Positive control for both reset vector sticky bits.
  @(negedge host);addr='h001234;rd_n=0;
  repeat(8)@(negedge host);spi73(0,which==2?'h4f:'h48);
  romsel_n=0;repeat(8)@(negedge host);spi73(0,which==2?'h5f:'h58);
  $display("BOOT case=%0d stage=0 accumulated=%02h",which,accumulated);
  if(which==2)begin
   @(negedge host);rd_n=1;romsel_n=1;addr='h7000;din=3;wr_n=0;
   repeat(8)@(negedge host);wr_n=1;repeat(8)@(negedge host);spi73(3,'h5f);
  end
 endtask
 initial begin
  boot_case(0);boot_case(1);boot_case(2);
  $display("PASS641 SPI73 boot observer: absent and pre-active reads indistinguishable; active vector and stage-3 control");$finish;
 end
 initial begin #2000000;$fatal(1,"boot641 watchdog");end
endmodule
