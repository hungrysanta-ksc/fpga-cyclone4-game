// SPDX-License-Identifier: MIT
// Short causal replay of game frame24/line193: current CHR data becomes the
// address low byte during PPUDATA/ALE overlap. Same70ns reader, no clock stall.
`timescale 1ns/1ps
module game147_prefetch_case #(parameter ENABLE=1,parameter realtime PHASE=3.5)(output reg done=0);
 reg clk=0,mem_clk=0,reset=1;
 always #23.280423 clk=~clk;initial begin #(PHASE);forever #2.9761905 mem_clk=~mem_clk;end
 reg cpu_early=0,hint=0,ppu_sample=0;reg [24:0] cpu_address=25'h3083f;reg [21:0] ppu_address=22'h21e150;
 wire [7:0] cpu_data,ppu_data;wire cpu_valid,ppu_valid,fault;wire [3:0] error_code;
 wire ready,request,response,error;wire [21:0] address,response_address;wire [7:0] data;
 nes_rom_early service(.clk(clk),.reset(reset),.cpu_address_valid(cpu_early),.ppu_address_valid(1'b1),
 .cpumem_addr(cpu_address),.cpumem_read(1'b0),.cpu_sample(1'b0),.ppumem_addr(ppu_address),.ppumem_read(1'b1),.ppu_sample(ppu_sample),
 .ppu_prefetch_valid(ENABLE && hint && ppu_valid),.ppu_prefetch_address({ppu_address[21:8],ppu_data}),
 .cpu_data(cpu_data),.ppu_data(ppu_data),.cpu_valid(cpu_valid),.ppu_valid(ppu_valid),
 .rom_ready(ready),.rom_request(request),.rom_address(address),.rom_response(response),.rom_error(error),.rom_response_address(response_address),.rom_data(data),
 .fault_trigger(),.fault_context(),.fault(fault),.error_code(error_code));
 wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem_clk),.reset(reset),
 .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),
 .rom_request(request),.rom_address(address),.rom_ready(ready),.rom_response(response),.rom_error(error),.rom_response_address(response_address),.rom_data(data),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
 function automatic [7:0] value(input [23:0] a);
  case(a)24'h21e150:value=8'hff;24'h21e158,24'h21e1ff:value=0;default:value=8'ha5;endcase
 endfunction
 wire selected=(!psram_1ce ^ !psram_2ce) && !psram_oe;
 wire [23:0] base={psram_address,psram_1ce,1'b0};
 assign #70 psram_data=selected?{value(base),value(base+24'd1)}:16'hzzzz;
 integer requests=0,speculative=0;
 always @(posedge clk)if(!reset && request)begin requests++;if(service.use_prefetch)speculative++;end
 initial begin
  #200;reset=0;repeat(12)@(negedge clk);
  // Prime the two already validated bytes from the recorded game prefix.
  service.ppu_cached=1;service.ppu_tag=17'h1e158;service.ppu_byte=0;
  service.ppu_previous_cached=1;service.ppu_previous_tag=17'h1e150;service.ppu_previous_byte=8'hff;
  cpu_early=1;repeat(7)@(negedge clk);hint=1;
  repeat(4)@(negedge clk);hint=0;ppu_address=22'h21e1ff;
  repeat(3)@(negedge clk);ppu_sample=1;
  if(ENABLE && (!ppu_valid || ppu_data!==0))$fatal(1,"PREFETCH147 data not ready phase%f",PHASE);
  @(negedge clk);ppu_sample=0;
  if(ENABLE)begin
   if(fault || speculative!=1)$fatal(1,"PREFETCH147 expected one correct speculation");
  end else if(!fault || error_code!=2 || speculative!=0)$fatal(1,"PREFETCH147 control failed to reproduce PPU deadline");
  $display("PASS PREFETCH147 enable=%0d phase=%f requests=%0d speculation=%0d error=%0d",ENABLE,PHASE,requests,speculative,error_code);done=1;
 end
endmodule
module game147_prefetch_tb;
 wire [3:0] done;
 game147_prefetch_case #(.ENABLE(1),.PHASE(3.5)) a(done[0]);
 game147_prefetch_case #(.ENABLE(0),.PHASE(3.5)) b(done[1]);
 game147_prefetch_case #(.ENABLE(1),.PHASE(0.0)) c(done[2]);
 game147_prefetch_case #(.ENABLE(0),.PHASE(0.0)) d(done[3]);
 initial begin wait(&done);$display("PASS PREFETCH147 ALL");$finish;end
 initial begin #100000;$fatal(1,"PREFETCH147 watchdog");end
endmodule
