// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module cache402_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,flush=0,request=0;reg[31:0]epoch=1;reg[21:0]address=0;reg[15:0]generation=1;
 wire[1:0]ready,idle,response,error,back_request,back_abort;wire[21:0]ra[2],ba[2];wire[15:0]rg[2],bg[2];wire[7:0]data[2];
 reg pending=0,back_response=0,back_error=0;reg[21:0]reply_address;reg[15:0]reply_generation;reg[7:0]reply_data;integer delay402=0,requests402=0,replies402=0,cycles402=0;
 reg inject402=0;
 nes_chr_cache402_reference ref402(.clk(clk),.reset(reset),.flush(flush),.request(request),.content_epoch(epoch),.address(address),.generation(generation),
 .ready(ready[0]),.idle(idle[0]),.response(response[0]),.error(error[0]),.response_address(ra[0]),.response_generation(rg[0]),.data(data[0]),
 .back_request(back_request[0]),.back_abort(back_abort[0]),.back_address(ba[0]),.back_generation(bg[0]),.back_ready(!pending),.back_idle(!pending),
 .back_response(back_response),.back_error(back_error),.back_response_address(reply_address),.back_response_generation(reply_generation),.back_data(reply_data));
 nes_chr_cache192 dut(.clk(clk),.reset(reset),.flush(flush),.request(request),.content_epoch(epoch),.address(address),.generation(generation),
 .ready(ready[1]),.idle(idle[1]),.response(response[1]),.error(error[1]),.response_address(ra[1]),.response_generation(rg[1]),.data(data[1]),
 .back_request(back_request[1]),.back_abort(back_abort[1]),.back_address(ba[1]),.back_generation(bg[1]),.back_ready(!pending),.back_idle(!pending),
 .back_response(back_response),.back_error(back_error),.back_response_address(reply_address),.back_response_generation(reply_generation),.back_data(reply_data));
 always @(posedge clk)begin
  if(reset)begin pending<=0;back_response<=0;delay402<=0;end
  else begin
   back_response<=0;
   if(pending)begin
    if(delay402==1)begin pending<=0;back_response<=1;replies402++;end else delay402<=delay402-1;
   end else if(back_request[0])begin
    pending<=1;delay402<=6;requests402++;reply_address<=ba[0];reply_generation<=bg[0];back_error<=inject402;
    reply_data<=ba[0][7:0]^ba[0][15:8]^ba[0][21:16];
   end
  end
 end
 always @(negedge clk)if(!reset)begin
  cycles402++;
  if(ready[0]!==ready[1]||idle[0]!==idle[1]||response[0]!==response[1]||error[0]!==error[1]||back_request[0]!==back_request[1]||back_abort[0]!==back_abort[1])
   $fatal(1,"cache402 timing cycle%0d state%0d/%0d scan%0d/%0d ready%b response%b request%b",cycles402,ref402.state,dut.state,ref402.scan,dut.scan,ready,response,back_request);
  if(response[0]&&(data[0]!==data[1]||ra[0]!==ra[1]||rg[0]!==rg[1]))$fatal(1,"cache402 value address%h data%h/%h",address,data[0],data[1]);
  if(back_request[0]&&(ba[0]!==ba[1]||bg[0]!==bg[1]))$fatal(1,"cache402 backing identity");
 end
 task tick;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
 task get402(input[21:0]a);begin
  while(ready!=3)tick();address=a;generation=generation+1'b1;request=1;tick();request=0;
  while(response!=3)tick();tick();
 end endtask
 reg[17:0]before402[16];
 initial begin
  repeat(3)tick();reset=0;repeat(3)tick();
  for(integer repeat402=0;repeat402<8;repeat402++)begin
   for(integer tag=0;tag<7;tag++)for(integer off=0;off<16;off++)get402((100+tag)*16+off);
   for(integer tag=0;tag<7;tag++)for(integer off=0;off<16;off++)get402((100+tag)*16+off);
   for(integer tag=0;tag<9;tag++)get402((200+tag+repeat402)*16+repeat402);
   epoch++;tick();tick();
  end
  inject402=1;get402(22'h34567);inject402=0;get402(22'h34567);
  get402(22'h3fffff);get402(22'h3fffff);get402(22'h005678);get402(22'h3f5678);get402(22'h005678);
  epoch=32'hffffffff;tick();tick();generation=16'hffff;get402(22'h3f5678);
  epoch=0;tick();tick();get402(22'h3f5678);
  while(ready!=3)tick();address=22'h45678;request=1;tick();request=0;wait(pending);@(negedge clk);flush=1;tick();
  for(integer i=0;i<16;i++)before402[i]=dut.metadata402[i];
  repeat(32)begin tick();if(response!=0)$fatal(1,"cache402 late DONE after STOP");
   for(integer i=0;i<16;i++)if(before402[i]!==dut.metadata402[i])$fatal(1,"cache402 STOP metadata write");end
  flush=0;tick();tick();get402(22'h45678);
  if(requests402!=replies402)$fatal(1,"cache402 undrained backing read");
  $display("PASS CACHE402 requests=%0d replies=%0d cycles=%0d lateDONE=32",requests402,replies402,cycles402);$finish;
 end
 initial begin #5000000;$fatal(1,"cache402 timeout");end
endmodule
