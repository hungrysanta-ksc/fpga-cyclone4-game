// Isolate the shipped source's sampled-release, empty-release and STOP edges.
`timescale 1ns/1ps
module tb_nes_release969;
 tb_nes_port914 #(.WINDOW957(1),.G(16'd909)) b();
 string action;
 integer grants=0;
 initial begin
   #1ms;
   $fatal(1,"release test timed out: action=%s grants=%0d",action,grants);
 end
 always @(posedge b.clk)
   if(b.source.shared_req && b.source.shared_ready) grants++;

 function automatic int valid_rows();
   int count=0;
   for(int i=0;i<256;i++) count+=int'(b.source.ahead.rows[i][b.source.ahead.WIDTH-1]);
   return count;
 endfunction

 initial begin
   logic [55:0] command;
   if(!$value$plusargs("action=%s",action) || !(action inside {"empty","sampled","stop"})) $fatal;
   #2;b.reset=1;repeat(10)@(negedge b.clk);b.reset=0;
   wait(b.cap_ready);@(negedge b.clk);b.cap_start=1;@(negedge b.clk);b.cap_start=0;
   repeat(280)@(negedge b.clk);
   command=56'heb8d0318010ea5;b.trace_run.ss964=0;#190;
   for(int i=55;i>=0;i--)begin
     b.trace_run.mosi964=command[i];#95;b.trace_run.sck964=1;#190;b.trace_run.sck964=0;#95;
   end
   b.trace_run.ss964=1;wait(grants==128);repeat(20)@(negedge b.clk);
   if(valid_rows()!=128)$fatal(1,"page not resident");
   if(action=="sampled")begin
     if(!b.cap_sample_ready)$fatal(1,"capture not ready");
     b.cap_addr=17'h31;b.cap_data=8'hd2;b.cap_sample=1;@(negedge b.clk);b.cap_sample=0;
   end
   b.cap_seal=1;@(negedge b.clk);b.cap_seal=0;repeat(4)@(negedge b.clk);
   if(action=="stop") b.stop=1; else b.release_capture951=1;
   #1;
   if(b.source.flush_capture951!==(action=="sampled") || b.source.shared_req)
     $fatal(1,"unexpected release qualification");
   @(negedge b.clk);b.stop=0;b.release_capture951=0;
   repeat(270)@(negedge b.clk);
   if(grants!=128 || valid_rows()!=(action=="empty"?128:0) || b.fault || b.batch_fault)
     $fatal(1,"bad rows=%0d grants=%0d",valid_rows(),grants);
   $display("PASS969 action=%s before=128 after=%0d grants=%0d",action,valid_rows(),grants);
   $finish;
 end
endmodule
