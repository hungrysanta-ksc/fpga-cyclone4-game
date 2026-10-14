// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Exact174 arbiter/exporter, synthetic memory/frame endpoints. No fill or CPU.
module native_fault176_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,core_request=0,fill_request=0,fill_abort=0;
 reg mem_response=0,mem_error=0;reg [21:0] mem_response_address=22'h1234;
 wire fault,core_ready,core_response,core_error,fill_ready,fill_idle,fill_response,fill_error,mem_request;
 wire [21:0] core_response_address,fill_response_address,mem_address;
 wire [7:0] core_data,fill_data;wire [15:0] fill_response_generation;
 nes_native_arbiter165 arb(.clk(clk),.reset(reset),.slot(1'b1),.core_safe(1'b1),
  .core_request(core_request),.core_address(22'h5678),.core_ready(core_ready),.core_response(core_response),.core_error(core_error),
  .core_response_address(core_response_address),.core_data(core_data),
  .fill_request(fill_request),.fill_abort(fill_abort),.fill_address(22'h1234),.fill_generation(16'd1),
  .fill_ready(fill_ready),.fill_idle(fill_idle),.fill_response(fill_response),.fill_error(fill_error),
  .fill_response_address(fill_response_address),.fill_response_generation(fill_response_generation),.fill_data(fill_data),
  .mem_ready(1'b1),.mem_request(mem_request),.mem_address(mem_address),.mem_response(mem_response),
  .mem_error(mem_error),.mem_response_address(mem_response_address),.mem_data(8'ha5),.fault(fault));
 reg owned=0;reg [15:0] generation=1;
 wire release_frame,tx_valid;wire [95:0] tx_data;wire [3:0] export_error;
 // Same fault masking as deployed174 nes_live_joint.sv; raw geometry is valid.
 nes_native_export165 #(.MAX_CYCLES(10000)) exporter(.clk(clk),.reset(reset),.enable(1'b1),
  .frame_owned(owned),.geometry_valid(!fault),.frame_generation(generation),
  .row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),.group_count(6'd1),.palette_count(6'd1),
  .release_frame(release_frame),.query(),.query_kind(),.query_index(),.query_generation(),
  .response(1'b0),.hit(1'b1),.data(64'd0),.fill_start(),.fill_busy(1'b0),.fill_done(1'b0),.fill_success(1'b0),.fill_error(4'd0),
  .byte_valid(1'b0),.byte_ready(),.byte_data(8'd0),.byte_tile(13'd0),.byte_lane(4'd0),.byte_kind(2'd0),.byte_generation(16'd0),
  .tx_valid(tx_valid),.tx_ready(1'b1),.tx_data(tx_data),.ack_valid(1'b0),.ack_ready(),.ack_accept(1'b0),.ack_generation(16'd0),
  .busy(),.error(export_error));
 integer begins=0,aborts=0,releases=0,checks=0,cases=0,n,k;
 always @(posedge clk)if(!reset)begin
  if(release_frame)begin owned<=0;releases<=releases+1;end
  if(tx_valid&&tx_data[95:93]==7)begin
   if(tx_data[76:64]==0)begins<=begins+1;
   if(tx_data[76:64]==2)begin
    if(tx_data[3:0]!=1)$fatal(1,"expected lease failure ABORT1");
    aborts<=aborts+1;
   end
  end
 end
 task check(input bit ok,input string why);begin checks++;if(!ok)$fatal(1,"%s",why);end endtask
 task fresh;
  begin reset=1;owned=0;fill_request=0;fill_abort=0;mem_response=0;mem_error=0;core_request=0;
   mem_response_address=22'h1234;repeat(3)@(negedge clk);reset=0;
   begins=0;aborts=0;releases=0;generation=1;@(negedge clk);
  end
 endtask
 task inject(input integer kind);
  begin
   fill_request=1;#1;check(fill_ready,"fill grant allowed");@(negedge clk);fill_request=0;
   if(kind==0)repeat(8)@(negedge clk);
   else begin mem_error=kind==1;mem_response_address=kind==2?22'h1235:22'h1234;end
   mem_response=1;@(negedge clk);mem_response=0;mem_error=0;repeat(2)@(negedge clk);
   check(fault&&fill_idle&&!fill_ready,"sticky failure drains but denies future fill");
   core_request=1;#1;check(core_ready&&mem_request&&mem_address==22'h5678,"core request still accepted");
   @(negedge clk);core_request=0;mem_response_address=22'h5678;mem_response=1;
   #1;check(core_response&&!core_error&&core_data==8'ha5,"core response still works");
   @(negedge clk);mem_response=0;
  end
 endtask
 initial begin
  for(k=0;k<3;k=k+1)begin
   fresh();owned=1;repeat(6)@(negedge clk);check(begins==1,"normal lease publishes BEGIN");
   inject(k);repeat(10)@(negedge clk);
   check(aborts==1&&releases==1&&!owned,"in-flight fault is NOT silent: ABORT precedes later rejection");
   for(n=0;n<3;n=n+1)begin generation=generation+1;owned=1;repeat(10)@(negedge clk);end
   check(begins==1&&aborts==1&&releases==4&&export_error==2,"later valid raw frames silently rejected before BEGIN");
   cases++;
   fresh();inject(k);owned=1;repeat(10)@(negedge clk);
   check(begins==0&&aborts==0&&releases==1&&export_error==2,"pre-existing fault case has no BEGIN or ABORT");
   cases++;
  end
  fresh();owned=1;repeat(6)@(negedge clk);check(!fault&&begins==1,"common reset restores admission");
  $display("PASS FAULT176 cases=%0d checks=%0d",cases,checks);$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
