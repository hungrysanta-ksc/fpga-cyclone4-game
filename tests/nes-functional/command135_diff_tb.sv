// SPDX-License-Identifier: MIT
// Two-state combinational equivalence against the exact134 encoded validator.
// Hierarchical assignments expose all Boolean causes, including unreachable
// combinations. Actual clocked retirement is tested by the separate SPI suite.
`timescale 1ns/1ps
module command135_diff_tb;
 reg mem_clk=0,reset=1,SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 reg load_ready=0,loaded=0,run_enable=0,boot_fault=0;
 reg [3:0] boot_error=0;reg [16:0] loaded_bytes=16;
 reg check_ready=0,check_response=0,check_fault=0;
 reg [16:0] check_response_address=0;reg [7:0] check_data=0;
 nes_rom_spi_check dut(.mem_clk(mem_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),
  .check_ready(check_ready),.check_response(check_response),.check_fault(check_fault),.check_response_address(check_response_address),.check_data(check_data));
 baseline135 refdut(.mem_clk(mem_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),
  .check_ready(check_ready),.check_response(check_response),.check_fault(check_fault),.check_response_address(check_response_address),.check_data(check_data));
 integer cases=0;reg [23:0] offset;
 initial begin
  #1;mem_clk=1;#1;mem_clk=0;reset=0;
  for(integer op=0;op<256;op++)for(integer flags=0;flags<2048;flags++)for(integer pattern=0;pattern<8;pattern++)begin
   case(pattern[1:0])0:offset=0;1:offset=16;2:offset=17;3:offset=24'hff0010;endcase
   load_ready=flags[0];loaded=flags[1];run_enable=flags[2];check_ready=flags[3];
   dut.command=op;refdut.command=op;dut.offset=offset;refdut.offset=offset;
   dut.check_enable=flags[4];refdut.check_enable=flags[4];
   dut.check_busy=flags[5];refdut.check_busy=flags[5];
   dut.check_done=flags[6];refdut.check_done=flags[6];
   dut.verified=flags[7];refdut.verified=flags[7];
   dut.offset_matches_next=flags[8];refdut.offset_matches_next=flags[8];
   dut.next_below_length=flags[9];refdut.next_below_length=flags[9];
   dut.next_matches_length=flags[10];refdut.next_matches_length=flags[10];
   dut.arg=pattern[2]?8'h36:8'ha5;refdut.arg=dut.arg;
   dut.checked_data=8'ha5;refdut.checked_data=8'ha5;
   #0.001;dut.pending_causes=dut.body_causes;#0.001;
   if(dut.pending_body_error!==refdut.body_error)$fatal(1,"CAUSE135 mismatch op=%h flags=%h pattern=%0d new=%h old=%h",op,flags,pattern,dut.pending_body_error,refdut.body_error);
   cases++;
  end
  if(cases!=4194304)$fatal(1,"CAUSE135 coverage");
  $display("PASS135 cause equivalence cases=%0d",cases);$finish;
 end
endmodule
