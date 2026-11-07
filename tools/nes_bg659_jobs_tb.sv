`timescale 1ns/1ps
module jobs_tb;
 reg clk=0,reset=1,stop=0,valid=0,ready=0;
 always #5 clk=~clk;
 reg[15:0] gen;reg[9:0] slot;reg[12:0] tag;reg[47:0] rows=48'hff6b646d2240;
 wire accept,out_valid,done,fault,req;wire[7:0] data;wire[4:0] idx;
 nes_tile205 #(.EXTERNAL_PLAN(1)) dut(.clk(clk),.reset(reset),.stop(stop),
 .lease_valid(1'b1),.lease_generation(gen),.mem_idle(1'b1),
 .plan_valid(valid),.plan_ready(accept),.plan_kind(2'd0),.plan_generation(gen),.plan_slot(slot),.plan_tag(tag),
 .plan_rows(rows),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
 .mem_request(req),.mem_ready(1'b1),.mem_response(1'b0),.mem_error(1'b0),.response_address(17'd0),
 .response_generation(16'd0),.response_data(8'd0),.out_valid(out_valid),.out_ready(ready),
 .out_data(data),.out_index(idx),.done(done),.fault(fault));
 integer fd,out,n=0,i;reg[15:0] g,s,t;reg[127:0] bytes;
 task launch;begin @(negedge clk);wait(accept);valid=1;@(negedge clk);valid=0;end endtask
 initial begin
  for(i=0;i<16;i++)rows[i*3+:3]=i/2;
  fd=$fopen("plans.txt","r");out=$fopen("descriptors.txt","w");
  repeat(3)@(negedge clk);reset=0;
  while($fscanf(fd,"%d %d %d",g,s,t)==3)begin
   gen=g;slot=s;tag=t;launch();
   for(i=0;i<16;i++)begin
    wait(out_valid);repeat(2)@(negedge clk);if(req||fault||idx!=i)$fatal(1,"not a descriptor");
    bytes={bytes[119:0],data};ready=1;@(negedge clk);ready=0;
   end
   if(!done)$fatal(1,"no retirement");
   $fwrite(out,"%d %d %032x\n",gen,slot,bytes);n++;
  end
  launch();wait(out_valid);@(negedge clk);stop=1;@(negedge clk);stop=0;if(out_valid||done)$fatal(1,"partial STOP");
  rows[0]=!rows[0];launch();wait(fault);if(out_valid||req)$fatal(1,"invalid BG escaped");
  if(n!=268)$fatal(1,"plan count");$display("PASS659 jobs %d",n);$finish;
 end
 initial begin repeat(100000)@(posedge clk);$fatal(1,"watchdog state=%d fault=%d",dut.state,fault);end
endmodule
