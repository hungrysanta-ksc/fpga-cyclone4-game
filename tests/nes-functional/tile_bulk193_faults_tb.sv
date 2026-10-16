// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tile_bulk193_faults_tb;
 reg nes_clk=0,host_clk=0,host_run=1;
 always #23.280423 nes_clk=!nes_clk;
 always #5.952 if(host_run)host_clk=!host_clk;
 reg reset=1,active=1,stop=0,source_fault=0,tile_valid=0,end_valid=0,consume=0;
 reg [7:0] tile_data=0;reg [4:0] tile_index=0;reg [5:0] tile_length=16;reg [1:0] tile_kind=0;
 reg [9:0] tile_slot=0;reg [15:0] tile_generation=12,end_generation=12;reg [31:0] token_seed=200,consume_token=0;
 reg [23:0] address=24'h400800;reg read_n=0,write_n=1;
 wire tile_ready,end_ready,chunk_ready,consume_error,oe_n,dir,fault,end_sealed,chunk_kind;
 wire [11:0] chunk_length;wire [31:0] chunk_token;wire [9:0] chunk_slot;wire [15:0] chunk_generation,sealed_generation;wire [7:0] data_out;
 nes_tile_bulk193 dut(.*);
 integer cases=0,n;reg [31:0] prior_token;
 task tick;begin @(posedge nes_clk);#1;end endtask
 task ht;begin @(posedge host_clk);#1;end endtask
 task fresh;
  begin host_run=1;reset=1;stop=0;source_fault=0;tile_valid=0;end_valid=0;tile_index=0;tile_generation=12;end_generation=12;
   tile_slot=0;tile_kind=0;tile_length=16;token_seed=token_seed+10;
   repeat(5)tick();@(negedge nes_clk);reset=0;while(!tile_ready)tick();end
 endtask
 task byte_at(input integer i);
  begin while(!tile_ready&&!fault)tick();@(negedge nes_clk);tile_index=i;tile_data=i+8'h40;tile_valid=1;
   tick();@(negedge nes_clk);tile_valid=0;end
 endtask
 task tile;
  begin for(n=0;n<16;n++)byte_at(n);end
 endtask
 task finish;
  begin while(!end_ready&&!fault)tick();@(negedge nes_clk);end_valid=1;tick();@(negedge nes_clk);end_valid=0;end
 endtask
 task failed;
  begin wait(fault);repeat(5)ht();if(chunk_ready||!oe_n)$fatal(1,"failed stream exposed");cases++;end
 endtask
 initial begin
  fresh();byte_at(1);failed();
  fresh();byte_at(0);tile_generation=13;byte_at(1);failed();
  fresh();tile();tile_generation=13;tile_slot=1;tile();failed();
  fresh();tile();end_generation=13;finish();failed();
  // Partial tile is never visible across STOP, followed by a fresh token.
  fresh();byte_at(0);@(negedge nes_clk);stop=1;tick();
  @(negedge nes_clk);stop=0;token_seed=token_seed+1;while(!tile_ready)tick();tile();finish();
  wait(chunk_ready);repeat(5)ht();if(chunk_length!=16||data_out!=8'h40||oe_n)$fatal(1,"partial STOP recovery");cases++;
  // Raw output gating is independent of the stopped host clock.
  prior_token=chunk_token;@(negedge host_clk);host_run=0;#1;stop=1;#1;
  if(!oe_n||chunk_ready)$fatal(1,"stopped clock STOP exposed old chunk");
  host_run=1;repeat(5)tick();@(negedge nes_clk);stop=0;token_seed=token_seed+1;
  while(!tile_ready)tick();tile();finish();wait(chunk_ready);repeat(5)ht();
  if(chunk_token==prior_token||chunk_length!=16||data_out!=8'h40||oe_n)$fatal(1,"fresh restart");cases++;
  // Source fault coherently resets the CDC and both chunk owners.
  source_fault=1;#1;if(!oe_n||chunk_ready)$fatal(1,"source fault raw output");
  repeat(5)tick();@(negedge nes_clk);source_fault=0;token_seed=token_seed+1;
  while(!tile_ready)tick();tile();finish();wait(chunk_ready);repeat(5)ht();
  if(fault||chunk_length!=16||oe_n)$fatal(1,"source fault recovery");cases++;
  fresh();token_seed=32'hffffffff;reset=1;repeat(5)tick();reset=0;while(!tile_ready)tick();tile();failed();
  $display("PASS BULK193FAULT cases=%0d",cases);$finish;
 end
 initial begin #10000000;$fatal(1,"fault test timeout");end
endmodule
