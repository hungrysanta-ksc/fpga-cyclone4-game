// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb_nes_page963;
 reg host=0,clk=0,reset=1,stop=0,ss=1,sck=0,mosi=0;
 always #6 host=~host;
 always #23 clk=~clk;
 wire source,valid,fault,write_plan,seal,retire;
 wire [25:0] payload,received;
 nes_plan_spi200 endpoint(.clk(host),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(1'b0),
   .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.page963(source),.payload963(payload),
   .plan_idle(1'b1),.plan_ready(1'b1),.plan_write(write_plan),.plan_seal(seal),.fault(fault),
   .retire(retire),.retire_done(1'b0),.end_sealed(1'b0),.chunk_ready(1'b0));
 nes_native_mailbox206 #(.WIDTH(26),.CONSUMER_CAPTURE(1)) mail(
   .src_clk(host),.dst_clk(clk),.reset(reset||stop),.src_valid(source),.src_data(payload),
   .dst_valid(valid),.dst_ready(1'b1),.dst_data(received));
 wire admitted=valid&&received[25:10]==16'd909;
 integer admitted_count=0,reads=0;
 reg demand=0,plan=0,allow=1,done=0,changed=0;
 reg [21:0] address=0,back=0;
 wire [21:0] physical;
 wire request,ready,response;
 wire [7:0] lo,hi;
 function automatic [7:0] data_byte(input [21:0] a);
   return a[7:0]^a[15:8]^(changed?8'hd3:8'h45);
 endfunction
 nes_e9_rows914 #(.COMPACT(1),.CHECK_HINT(1),.SINGLE_READ(1),.COMPLETE_ROW_SET(1)) rows(
   .clk(clk),.reset(reset),.flush_rom(stop),.invalidate(stop),.empty_capture(1'b1),
   .page963(admitted),.page_base963(received[9:0]),.plan963(plan),.hint(1'b0),.tag(13'd0),
   .mask(8'd0),.demand(demand),.pair(1'b1),.address(address),.ready(ready),.response(response),
   .lo(lo),.hi(hi),.request(request),.physical_address(physical),.grant_ready(allow),
   .reply(done&&!stop),.physical_done(done),.physical_error(1'b0),.reply_address(back),
   .physical_lo(data_byte(back)),.physical_hi(~data_byte(back)));
 always @(posedge host) if(!reset&&!stop && (fault||write_plan||seal||retire)) $fatal(1,"advisory changed plan");
 always @(posedge clk)begin
   done<=request&&allow;
   if(admitted)begin
     if(received[9:0]!=384)$fatal(1,"bad base");
     admitted_count<=admitted_count+1;
   end
   if(request&&allow)begin
     if(rows.aux952 && reads<128 && physical!==22'h20c000+16*(reads/8)+(reads%8))
       $fatal(1,"bad address %h row %d",physical,reads);
     reads<=reads+1;back<=physical;
   end
 end
 task automatic send(input [55:0] command,input integer len);
   ss=0; #190;
   for(int i=0;i<len;i++)begin mosi=command[55-i];#95;sck=1;#190;sck=0;#95;end
   ss=1; repeat(12) @(negedge clk);
 endtask
 task automatic get_row(input integer ordinal,input integer misses);
   integer prior;
   @(negedge clk);prior=reads;address=22'h20c000+16*(ordinal/8)+(ordinal%8);demand=1;
   do @(posedge clk);while(!ready);
   @(negedge clk);demand=0;while(!response)@(negedge clk);
   if(reads-prior!=misses||lo!==data_byte(address)||hi!==~data_byte(address))$fatal(1,"wrong read %d",ordinal);
 endtask
 task automatic clear_rom;
   stop=1;#1;if(request||response)$fatal(1,"STOP");
   repeat(5)@(negedge clk);stop=0;repeat(270)@(negedge clk);
 endtask
 initial begin
   repeat(5)@(negedge clk);reset=0;clear_rom();
   send(56'heb8d03000cd3a5,56); send(56'heb8d03000cd2a5,53);send(56'heb8b03400cfda5,56);
   if(reads||admitted_count)$fatal(1,"partial, bad CRC or stale generation");
   allow=0;send(56'heb8d03000cd2a5,56);wait(request);
   repeat(7)@(negedge clk);if(physical!=22'h20c000||reads!=0)$fatal(1,"grant wait");
   allow=1;wait(reads==128);repeat(10)@(negedge clk);
   for(int n=0;n<128;n++)get_row(n,0);
   if(reads!=128||admitted_count!=1)$fatal(1,"unexpected refill");
   clear_rom();send(56'heb8d03000cd2a5,56);wait(reads>=132);
   @(negedge clk);plan=1;#1;if(request)$fatal(1,"plan priority");
   @(negedge clk);plan=0;repeat(5)@(negedge clk);if(request)$fatal(1,"restarted after plan");
   clear_rom();send(56'heb8d03000cd2a5,56);wait(done);@(negedge clk);changed=1;clear_rom();get_row(0,1);
   $display("PASS963 SPI CRC and generation, 128 tagged grants and two-plane hits, backpressure, plan priority, STOP and changed ROM");
   $finish;
 end
 initial begin #800000;$fatal(1,"timeout grants=%d admitted=%d",reads,admitted_count);end
endmodule
