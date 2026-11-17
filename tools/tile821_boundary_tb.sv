`timescale 1ns/1ps
module tile821_boundary_tb;
  bit nes_clk, host_clk, reset=1, active=1, stop, source_fault;
  bit plan_valid, plan_taken, tile_valid, end_valid, consume;
  bit [1:0] plan_kind, tile_kind;
  bit [9:0] plan_slot, tile_slot;
  bit [15:0] plan_generation=1, tile_generation=1, end_generation=1;
  bit [7:0] tile_data;
  bit [4:0] tile_index;
  bit [5:0] tile_length;
  bit [31:0] token_seed=11, consume_token;
  bit [23:0] address;
  bit read_n=1, write_n=1;
  wire plan_permit, tile_ready, end_ready, chunk_ready, chunk_kind, consume_error;
  wire fault, witness_host, witness_reject, end_sealed, oe_n, dir;
  wire [15:0] chunk_generation, sealed_generation;
  wire [31:0] chunk_token;
  wire [11:0] chunk_length;
  wire [9:0] chunk_slot;
  wire [7:0] data_out;
  realtime split_ns, end_ns;
  nes_tile_bulk206 dut(.*);
  always #23.281 nes_clk=~nes_clk;
  always #5.952 host_clk=~host_clk;
  task automatic tile(input bit [1:0] kind, input int slot, input int size);
    @(negedge nes_clk);
    tile_kind=kind; tile_slot=slot; tile_length=size;
    for(int j=0;j<size;j++)begin
      while(!tile_ready) @(negedge nes_clk);
      tile_index=j; tile_data=j; tile_valid=1;
      @(negedge nes_clk);
    end
    tile_valid=0;
  endtask
  initial begin
    repeat(8) @(negedge nes_clk);
    reset=0;
    wait(tile_ready===1);
    tile(2,0,16);
    @(negedge nes_clk);
    plan_kind=1;plan_slot=3;plan_valid=1;split_ns=$realtime;
    wait(chunk_ready===1);
    if(chunk_kind || chunk_length!=16 || chunk_token!=11) $fatal(1,"split");
    $display("BG HEAD split_to_ready_ns=%0.3f",$realtime-split_ns);
    @(negedge nes_clk);
    while(!plan_permit) @(negedge nes_clk);
    plan_taken=1;
    @(negedge nes_clk);
    plan_valid=0;plan_taken=0;
    tile(1,3,32);
    while(!end_ready) @(negedge nes_clk);
    end_valid=1;end_ns=$realtime;
    @(negedge nes_clk);end_valid=0;
    wait(end_sealed===1);
    if(chunk_token!=11 || chunk_length!=16 || fault) $fatal(1,"head ownership");
    $display("OBJ END to sealed_ns=%0.3f",$realtime-end_ns);
    repeat(20) @(negedge host_clk);
    consume_token=11;consume=1;
    @(negedge host_clk);consume=0;
    if(!chunk_ready || !chunk_kind || chunk_length!=32 || chunk_token!=12 || consume_error) $fatal(1,"second head");
    stop=1;
    @(negedge host_clk);
    if(chunk_ready) $fatal(1,"STOP");
    $display("PASS TILE821 SPLIT END HEAD STOP");
    $finish;
  end
  initial #50000 $fatal(1,"timeout");
endmodule
