// SPDX-License-Identifier: MIT
// Two legal backend/input histories with the same terminal PPU deadline tuple.
// This proves why the terminal tuple cannot select a physical root cause.
`timescale 1ns/1ps
module service157_tb;
 reg clk=0,reset=1,cpu_read=0,ppu_read=0,ppu_sample=0,ready=1,response=0;
 always #23.280423 clk=~clk;
 reg [21:0] ppu_addr=22'h3a0000;
 reg [24:0] cpu_addr=25'h10000;
 wire [7:0] cpu_data,ppu_data;wire cpu_valid,ppu_valid,request,trigger,fault;
 wire [21:0] address;wire [3:0] error;wire [63:0] fault_tuple;wire [11:0] flags;
 nes_rom_early service(.clk(clk),.reset(reset),.ppu_prefetch_valid(1'b0),.ppu_prefetch_address(22'h217a18),
  .cpu_address_valid(cpu_read),.ppu_address_valid(ppu_read),.cpumem_addr(cpu_addr),.cpumem_read(cpu_read),.cpu_sample(1'b0),
  .ppumem_addr(ppu_addr),.ppumem_read(ppu_read),.ppu_sample(ppu_sample),.cpu_data(cpu_data),.ppu_data(ppu_data),.cpu_valid(cpu_valid),.ppu_valid(ppu_valid),
  .rom_ready(ready),.rom_request(request),.rom_address(address),.rom_response(response),.rom_error(1'b0),.rom_response_address(22'h10000),.rom_data(8'ha5),
  .fault_trigger(trigger),.fault_context(fault_tuple),.fault(fault),.error_code(error),.history_flags157(flags));
 wire [95:0] sample={9'd193,9'd8,flags,address,22'h217a18,ppu_addr};
 wire [55:0] page;
 reg [7:0] command=0;
 nes_ppu_history157 history(clk,reset,!reset,trigger,sample,command,page);
 reg [63:0] final_context[0:1];reg [95:0] rows[0:1][0:7];integer mode,i;
 initial begin
  for(mode=0;mode<2;mode++)begin
   @(negedge clk);reset=1;cpu_read=0;ppu_read=0;ppu_sample=0;ready=1;response=0;ppu_addr=22'h3a0000;
   repeat(3)@(negedge clk);reset=0;
   for(i=0;i<8;i++)begin
    cpu_read=(mode==0 && i==0);
    cpu_addr=i>=6?25'h10001:25'h10000;
    ppu_read=i>=(mode==0?3:5);ppu_addr=ppu_read?22'h217a18:22'h3a0000;
    ready=(i==0 || i==5 || (mode==1 && i<5));response=(mode==0 && i==5);ppu_sample=(i==7);
    @(posedge clk);rows[mode][i]=sample;
    if(i==7)begin
     if(!trigger || fault_tuple!==64'he200c2f430217a18)$fatal(1,"terminal %h",fault_tuple);
     final_context[mode]=fault_tuple;
    end
    @(negedge clk);
   end
   if(!fault||error!=2)$fatal(1,"deadline not retained");
   command=8'hae;repeat(3)@(negedge clk);if(page!=={8'he0,rows[mode][7][95:48]})$fatal(1,"fault edge upper");
   command=8'haf;repeat(3)@(negedge clk);if(page!=={8'he0,rows[mode][7][47:0]})$fatal(1,"fault edge lower");
  end
  if(final_context[0]!==final_context[1] || rows[0][0]===rows[1][0] || rows[0][3]===rows[1][3])$fatal(1,"not discriminating");
  for(mode=0;mode<2;mode++)for(i=0;i<8;i++)$display("HISTORY157 cause=%0d tick=%0d value=%h",mode,i,rows[mode][i]);
  $display("PASS157 same first-fault snapshot, distinguish prior CPU occupancy and later exposed PPU demand; synthetic not hardware replay");$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
