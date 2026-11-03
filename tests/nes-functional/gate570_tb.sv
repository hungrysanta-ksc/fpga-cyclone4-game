// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module gate570_tb;
 reg host_clk=0,nes_clk=0,host_on=1,nes_on=1,reset=0;
 reg lease_fault=0,core_fault=0,immutable=1,ss=1,sck=0,mosi=0;
 always #5952 if(host_on)host_clk=!host_clk;
 initial begin if($test$plusargs("SHIFT"))#11000;forever #23281 if(nes_on)nes_clk=!nes_clk;end
 wire hf,nf,retire_commit;
 nes_direct206 dut(.host_clk(host_clk),.nes_clk(nes_clk),.reset(reset),.transport_fault(1'b0),
  .lease_valid(1'b1),.lease_fault(lease_fault),.retire_permitted(1'b1),.captured_generation(16'd954),
  .captured_epoch(32'd1),.live_epoch(32'd1),.source_ready(immutable),.source_is_rom(1'b1),.source_writing(1'b0),
  .core_fault(core_fault),.qualified_slot(1'b1),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),
  .mem_ready(1'b0),.mem_response(1'b0),.mem_error(1'b0),.mem_response_address(22'd0),.mem_data(8'd0),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.address(24'h6040),.read_n(1'b1),.write_n(1'b1),
  .data_in(8'd0),.host_fault(hf),.nes_fault(nf),.retire_commit(retire_commit));
 reg [7:0] raw[0:195];
 bit guarded,ingress;
 task byte_io(input [7:0] b);
  for(int j=7;j>=0;j--)begin mosi=b[j];#190476;sck=1;#190476;sck=0;end
 endtask
 task data_frame(input int a,n,input bit finish=1);
  ss=0;#80000;for(int i=0;i<n;i++)byte_io(raw[a+i]);
  #80000;if(finish)begin ss=1;#200000;end
 endtask
 task restart;
  reset=1;lease_fault=0;core_fault=0;immutable=1;ss=1;host_on=1;nes_on=1;
  repeat(6)@(negedge nes_clk);reset=0;repeat(16)@(negedge nes_clk);
  if(!dut.pi||!dut.pr||nf||hf||dut.spi_fault||dut.endpoint.accepted!=0)$fatal(1,"restart");
 endtask
 task quiet_plan;
  if(dut.pr||dut.pv||dut.ev||dut.transport.word_valid||retire_commit||!dut.oe_n)$fatal(1,"plan leak");
 endtask
 integer resumes=0;
 task finish_fault;
  // nf is sticky independently of the plan reset. Reactivate the two
  // clocks separately and require a common reset before another admission.
  nes_on=1;wait(nf);#100;quiet_plan();
  host_on=1;wait(hf);repeat(12)@(negedge host_clk);
  if(!dut.spi_fault||!nf)$fatal(1,"fault lost");
  quiet_plan();resumes++;
 endtask
 task producer(input int kind);
  if(kind==2)begin
   @(negedge nes_clk);host_on=0;immutable=0;
   @(posedge nes_clk);#100;nes_on=0;
   if(!dut.tile_fault||nf)$fatal(1,"tile producer last edge");
  end else begin
   @(negedge nes_clk);nes_on=0;host_on=0;
   if(kind==0)lease_fault=1;else core_fault=1;
  end
  #100;
 endtask
 initial begin
  guarded=$test$plusargs("GUARDED");ingress=$test$plusargs("INGRESS");
  $readmemh("requests.hex",raw);
  // One accepted bank stalls for ROM. The next slot must still have credit.
  for(int k=0;k<3;k++)begin
   restart();data_frame(0,32);wait(dut.pv&&dut.pr);
   producer(k);
   if(nf||hf||dut.pr!==!guarded)$fatal(1,"pre-latch credit %0d",k);
   if(guarded)quiet_plan();
   $display("PRE570 kind=%0d writable=%0d nf=%0d",k,dut.pr,nf);
   finish_fault();
  end
  // Seal both slots. Stop host before the NES latches its fault. No host
  // edge may be needed to remove the visible word or prevent its retirement.
  restart();data_frame(0,32);data_frame(32,121);
  if(!dut.transport.pending||dut.pr||dut.endpoint.accepted!=2||!dut.transport.word_valid)$fatal(1,"two slots");
  @(negedge host_clk);host_on=0;lease_fault=1;
  wait(nf);#100;nes_on=0;quiet_plan();finish_fault();
  // Fault after the entire E9 trailer but before the SS rising edge. Resume
  // host alone: an accepted-count increment is externally visible in E8.
  restart();data_frame(0,32,0);
  if(!dut.endpoint.can_write||dut.endpoint.count!=32||dut.transport.count!=24)$fatal(1,"trailer");
  producer(1);ss=1;host_on=1;repeat(12)@(negedge host_clk);
  if(dut.endpoint.accepted!==(ingress?16'd0:16'd1))$fatal(1,"E9 accounting");
  if(guarded&&(!dut.hc||dut.transport.pending||dut.transport.count!=0))$fatal(1,"aborted plan admitted");
  $display("TRAILER570 accepted=%0d stored=%0d",dut.endpoint.accepted,dut.transport.count);
  finish_fault();restart();data_frame(0,32);if(dut.endpoint.accepted!=1||nf||hf||resumes!=5)$fatal(1,"recovery");
  $display("PASS570 TOP recoveries=5");$finish;
 end
 initial begin #2000000000;$fatal(1,"timeout state=%d nf=%d hf=%d",dut.transport.state,nf,hf);end
endmodule
