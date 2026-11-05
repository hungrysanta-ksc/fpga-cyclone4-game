// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module nes_oe612_case #(parameter N=16, PH=0)(output reg done=0);
 reg clk=0,mem_clk=0,on=1,reset=1,check_mode=0,check_request=0,rom_request=0;
 reg [21:0] check_address=0,rom_address=0;
 always #23281 if(on)clk=!clk;
 initial begin #(PH);forever #2976 if(on)mem_clk=!mem_clk;end
 wire [21:0] pa[0:1],ca[0:1],ra[0:1];
 wire [7:0] cd[0:1],rd[0:1];
 wire [1:0] cr,cp,rr,rp,re,c1,c2,oe,we,bh,bl;
 wire [15:0] data=pa[0][15:0]^16'ha57c;
 nes_rom_physical #(.READ_CYCLES(N),.HOLD_SOURCE_IN_CHECK(1)) dut(
 .clk(clk),.mem_clk(mem_clk),.reset(reset),.check_mode(check_mode),.check_request(check_request),.check_address(check_address),
 .check_ready(cr[0]),.check_response(cp[0]),.check_response_address(ca[0]),.check_data(cd[0]),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rr[0]),.rom_response(rp[0]),.rom_error(re[0]),.rom_response_address(ra[0]),.rom_data(rd[0]),
 .psram_address(pa[0]),.psram_1ce(c1[0]),.psram_2ce(c2[0]),.psram_oe(oe[0]),.psram_we(we[0]),.psram_bhe(bh[0]),.psram_ble(bl[0]),.psram_data(data));
 nes_rom_physical_ref #(.READ_CYCLES(N),.HOLD_SOURCE_IN_CHECK(1)) refdut(
 .clk(clk),.mem_clk(mem_clk),.reset(reset),.check_mode(check_mode),.check_request(check_request),.check_address(check_address),
 .check_ready(cr[1]),.check_response(cp[1]),.check_response_address(ca[1]),.check_data(cd[1]),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rr[1]),.rom_response(rp[1]),.rom_error(re[1]),.rom_response_address(ra[1]),.rom_data(rd[1]),
 .psram_address(pa[1]),.psram_1ce(c1[1]),.psram_2ce(c2[1]),.psram_oe(oe[1]),.psram_we(we[1]),.psram_bhe(bh[1]),.psram_ble(bl[1]),.psram_data(data));
 integer samples=0,reads=0,cancels=0;
 always @(posedge clk or negedge clk or posedge mem_clk or negedge mem_clk or reset)begin
  #2;
  if($time>10)begin
   if({cr[0],cp[0],rr[0],rp[0],re[0],c1[0],c2[0],oe[0],we[0],bh[0],bl[0],pa[0],ca[0],ra[0],cd[0],rd[0]} !==
      {cr[1],cp[1],rr[1],rp[1],re[1],c1[1],c2[1],oe[1],we[1],bh[1],bl[1],pa[1],ca[1],ra[1],cd[1],rd[1]})
      $fatal(1,"612 miter N=%0d PH=%0d time=%0t",N,PH,$time);
   if(reset&&(!oe[0]||!c1[0]||!c2[0]||rp[0]||cp[0]))$fatal(1,"612 reset outputs");
   samples=samples+1;
  end
 end
 task restart(input bit mode);
  begin reset=1;rom_request=0;check_request=0;#17000;check_mode=mode;on=1;#11000;reset=0;repeat(8)@(negedge clk);end
 endtask
 task issue(input bit mode,input integer address);
  begin
   if(mode)begin wait(cr[0]);@(negedge mem_clk);check_address=address;check_request=1;@(negedge mem_clk);check_request=0;end
   else begin wait(rr[0]);@(negedge clk);rom_address=address;rom_request=1;@(negedge clk);rom_request=0;end
  end
 endtask
 integer mode,i,stage;reg [7:0] expected;
 initial begin
  #100;
  for(mode=0;mode<2;mode=mode+1)begin
   restart(mode);
   for(i=0;i<32;i=i+1)begin
    issue(mode,22'h200000+i*257);
    if(mode)wait(cp[0]);else wait(rp[0]);#3;
    expected=(i*257)&1 ? data[7:0]:data[15:8];
    if((mode?cd[0]:rd[0])!==expected)$fatal(1,"612 read byte");
    reads=reads+1;repeat(3)@(negedge clk);
   end
   for(stage=0;stage<4;stage=stage+1)begin
    restart(mode);
    fork
    issue(mode,22'h200003);
    begin
    // SETUP / ACTIVE / HOLD / RELEASE; pause both clocks, then cancel.
    wait(dut.state==stage+1);#17;on=0;#173;reset=1;rom_request=0;check_request=0;#5;
    if(!oe[0]||!c1[0]||!c2[0]||rp[0]||cp[0])$fatal(1,"612 stopped clock kill");
    #113;reset=0;#101;
    if(!oe[0])$fatal(1,"612 short reset lost");
    on=1;repeat(12)@(negedge clk);
    if(rp[0]||cp[0])$fatal(1,"612 stale completion");cancels=cancels+1;
    end
    join
   end
  end
  restart(0);issue(0,22'h200001);wait(rp[0]);reads=reads+1;
  $display("PASS612 N=%0d PH=%0d reads=%0d stopped_cancel=%0d comparisons=%0d",N,PH,reads,cancels,samples);done=1;
 end
endmodule
module nes_oe612_tb;
 wire [3:0] done;
 nes_oe612_case #(16,0) a(done[0]);nes_oe612_case #(16,3100) b(done[1]);
 nes_oe612_case #(1,0) c(done[2]);nes_oe612_case #(3,3100) d(done[3]);
 initial begin wait(&done);$display("PASS612 all");$finish;end
 initial begin #100000000;$fatal(1,"612 watchdog");end
endmodule
