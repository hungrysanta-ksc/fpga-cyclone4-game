// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module held575 #(parameter CAPTURE=0, WIDTH=16, PERIOD=45454)(
 input wire src_clk,dst_clk,reset, output reg finished=0);
 reg valid=0,ready=0;reg [WIDTH-1:0] input_word=0;
 wire src_ready,dst_valid;wire [WIDTH-1:0] output_word;
 nes_native_mailbox206 #(.WIDTH(WIDTH),.CONSUMER_CAPTURE(CAPTURE)) dut(
 .src_clk(src_clk),.dst_clk(dst_clk),.reset(reset),.src_valid(valid),.src_ready(src_ready),
 .src_data(input_word),.dst_valid(dst_valid),.dst_ready(ready),.dst_data(output_word));
 reg [WIDTH-1:0] expected=0;reg owned=0;
 time published,min_capture=64'hffffffffffffffff;
 integer accepted=0,consumed=0,checks=0;
 always @(posedge src_clk or posedge reset)
  if(reset)begin owned=0;expected=0;end
  else if(valid&&src_ready)begin
   expected=input_word;published=$time;accepted++;owned=1;
  end else if(src_ready)owned=0;
 always @(negedge src_clk)if(!reset&&owned)begin
  if(dut.held!==expected)$fatal(1,"producer changed outstanding data");
  checks++;
 end
 always @(posedge dst_clk)if(!reset&&!dut.dst_reset)begin
  if(dut.capture)begin
   if($time-published<2*PERIOD)$fatal(1,"data captured too soon");
   if($time-published<min_capture)min_capture=$time-published;
  end
  if(dst_valid&&ready)begin
   if(output_word!==expected)$fatal(1,"mixed or stale data");
   consumed++;
  end
 end
 initial begin
  wait(!reset);
  for(int i=0;i<64;i++)begin
   @(negedge src_clk);while(!src_ready)@(negedge src_clk);
   input_word=WIDTH'(32'hfe51a00f^(i*32'h1234567));valid=1;
   @(negedge src_clk);valid=0;
   // Backpressure spans both short and long ownership intervals.
   repeat(i%7+1)@(negedge dst_clk);
   ready=1;wait(consumed==i+1);@(negedge dst_clk);ready=0;
  end
  wait(src_ready);
  if(accepted!=64||consumed!=64||checks==0)$fatal(1,"mailbox count");
  $display("HELD575 capture=%0d width=%0d accepted=%0d checks=%0d min_ps=%0d budget_ps=%0d",CAPTURE,WIDTH,accepted,checks,min_capture,2*PERIOD);
  finished=1;
 end
endmodule

module boundary575_tb;
 reg host=0,mem=0,nes=0,reset=1;
 always #5952 host=!host;
 always #2976 mem=!mem;
 initial begin if($test$plusargs("SHIFT"))#11000;forever #22727 nes=!nes;end
 wire plan_done,tile_done,rom_done,reset_done;
 held575 #(.CAPTURE(1),.WIDTH(16),.PERIOD(45454)) plan(host,nes,reset,plan_done);
 held575 #(.CAPTURE(0),.WIDTH(32),.PERIOD(11904)) tiles(nes,host,reset,tile_done);
 rom575 reader(nes,mem,reset,rom_done);
 reset575 reset_audit(nes,mem,reset_done);
 initial begin #50000;reset=0;wait(plan_done&&tile_done&&rom_done&&reset_done);$display("PASS575 HELD128 ROM64 RESET32");$finish;end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule

module reset575(input wire clk,mem_clk,output reg finished=0);
 reg reset=1;reg [4:0] commands=0;
 wire fault;wire [15:0] psram;
 integer clear_edges=0;
 nes_rom_boot dut(.clk(clk),.mem_clk(mem_clk),.reset(reset),.read_reset(1'b0),
 .check_enable(1'b0),.check_request(1'b0),.check_address(19'd0),
 .load_begin(commands[0]),.load_end(commands[1]),.start(commands[2]),.stop(commands[3]),
 .load_valid(commands[4]),.load_chr32(1'b0),.load_data(8'd0),.boot_fault(fault),
 .rom_request(1'b0),.rom_address(22'd0),.psram_data(psram));
 always @(negedge fault)begin
  #1;
  if(!dut.loader.active_reset||!dut.reader_reset)$fatal(1,"fault clear released reader without common reset");
  clear_edges++;
 end
 initial begin
  #50000;reset=0;repeat(8)@(negedge mem_clk);
  commands=5'b00100;@(negedge mem_clk);commands=0;
  if(!fault||!dut.reader_reset)$fatal(1,"invalid START did not latch fault");
  for(int i=0;i<32;i++)begin
   commands=5'(i);@(negedge mem_clk);
   if(!fault||!dut.reader_reset||dut.run_enable)$fatal(1,"command cleared sticky fault");
  end
  commands=0;reset=1;#2;
  if(fault||!dut.reader_reset)$fatal(1,"common reset order");
  @(negedge mem_clk);reset=0;repeat(8)@(negedge mem_clk);
  if(fault||!dut.reader_reset||dut.run_enable||clear_edges<1)$fatal(1,"post-reset ownership");
  $display("RESET575 commands=32 fault_clear_edges=%0d",clear_edges);finished=1;
 end
endmodule

module rom575(input wire clk,mem_clk,reset,output reg finished=0);
 reg request=0;reg [21:0] address=0;
 wire ready,response;wire [21:0] response_address;wire [7:0] data;
 nes_rom_physical #(.READ_CYCLES(16),.HOLD_SOURCE_IN_CHECK(1)) dut(
 .clk(clk),.mem_clk(mem_clk),.reset(reset),.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),
 .rom_request(request),.rom_address(address),.rom_ready(ready),.rom_response(response),
 .rom_response_address(response_address),.rom_data(data),.psram_data(16'h5aa5));
 time launched,min_address=64'hffffffffffffffff;
 integer count=0,checks=0;
 reg owned=0;reg [21:0] held;
 always @(posedge clk)if(!reset)begin
  if(response)begin
   if(response_address!==held||data!==(held[0]?8'ha5:8'h5a))$fatal(1,"wrong ROM reply");
   count++;owned=0;
  end
  if(request&&ready)begin held=address;launched=$time;owned=1;end
 end
 always @(negedge clk)if(owned)begin
  if(dut.address_hold!==held)$fatal(1,"ROM address changed before ACK");
  checks++;
 end
 always @(posedge mem_clk)if(!dut.mr&&dut.state==0&&dut.pending)begin
  if($time-launched<11904)$fatal(1,"ROM address captured too early");
  if($time-launched<min_address)min_address=$time-launched;
 end
 initial begin
  wait(!reset);
  for(int i=0;i<64;i++)begin
   @(negedge clk);while(!ready)@(negedge clk);
   address=22'(i*7919);request=1;
   @(negedge clk);request=0;
   wait(count==i+1);
  end
  if(checks==0)$fatal(1,"no ROM ownership checks");
  $display("ROM575 reads=%0d checks=%0d min_ps=%0d budget_ps=11904",count,checks,min_address);
  finished=1;
 end
endmodule
