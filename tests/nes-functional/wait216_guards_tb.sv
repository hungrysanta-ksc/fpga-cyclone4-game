// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module wait216_guards_tb #(parameter EXTERNAL=1);
 reg clk=0,reset=1,stop=0,lease=1,pv=0,grant=1,credit=1,answer=1;
 always #5 clk=!clk;
 wire pr,req,cancel,ov,busy,fault,done;wire [16:0] addr;wire [15:0] mg;
 wire [7:0] data;wire [4:0] index;
 reg response=0,error=0;reg [16:0] ra=0;reg [15:0] rg=0;reg [7:0] rd=0;
 integer bad=0,checks=0,accepted=0;reg [7:0] held;reg [4:0] held_index;reg [31:0] held_cycles;
 nes_tile205 #(.EXTERNAL_PLAN(EXTERNAL),.MAX_CYCLES(128)) dut(
 .clk(clk),.reset(reset),.stop(stop),.lease_valid(lease),.lease_generation(16'd7),
 .plan_valid(pv),.plan_ready(pr),.plan_kind(2'd0),.plan_generation(16'd7),.plan_slot(10'd1),
 .plan_tag(13'd3),.plan_rows(48'hfac688fac688),.plan_mask(8'hff),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
 .mem_idle(1'b1),.mem_ready(grant),.mem_request(req),.mem_cancel(cancel),.mem_address(addr),.mem_generation(mg),
 .mem_response(response),.mem_error(error),.response_address(ra),.response_generation(rg),.response_data(rd),
 .out_valid(ov),.out_ready(credit),.out_data(data),.out_index(index),.out_length(),.out_kind(),.out_slot(),.out_generation(),
 .busy(busy),.fault(fault),.done(done));
 always @(posedge clk)begin
  response<=0;
  if(!reset&&req&&grant&&answer)begin
   response<=1;ra<=addr^(bad==2?17'd1:17'd0);rg<=mg^(bad==3?16'd1:16'd0);rd<=addr[7:0]^8'h5a;error<=bad==1;
  end
  if(reset)accepted<=0;else if(ov&&credit)accepted<=accepted+1;
 end
 task tick;begin @(posedge clk);#1;end endtask
 task fresh;
  begin @(negedge clk);reset=1;stop=0;lease=1;pv=0;grant=1;credit=1;answer=1;bad=0;
   repeat(4)tick();@(negedge clk);reset=0;repeat(2)tick();end
 endtask
 task submit;
  begin if(!pr)$fatal(1,"not ready");@(negedge clk);pv=1;tick();@(negedge clk);pv=0;end
 endtask
 initial begin
  // Stalls longer than the execution budget preserve immutable output and age.
  fresh();grant=0;submit();held_cycles=dut.cycles;
  repeat(300)begin tick();if(fault||!req||ov||dut.cycles!=held_cycles)$fatal(1,"admission aged");end
  @(negedge clk);grant=1;wait(accepted==7);@(negedge clk);credit=0;wait(ov);@(negedge clk);
  held=data;held_index=index;held_cycles=dut.cycles;
  repeat(300)begin tick();if(fault||!ov||data!==held||index!=held_index||dut.cycles!=held_cycles)$fatal(1,"output aged/changed");end
  @(negedge clk);credit=1;wait(done);tick();if(accepted!=16||fault)$fatal(1,"resume failed");checks++;
  // A granted read without response still expires; no forced counter injection.
  fresh();answer=0;submit();repeat(130)tick();
  if(!fault||busy||ov||!cancel||accepted)$fatal(1,"missing response not rejected");checks++;
  // Address, generation and explicit reader errors stay terminal.
  for(integer k=1;k<=3;k++)begin
   fresh();bad=k;submit();repeat(8)tick();
   if(!fault||busy||ov||!cancel||accepted)$fatal(1,"bad response accepted %0d",k);checks++;
  end
  // Cancellation is not suspended with the execution timer.
  for(integer k=0;k<3;k++)begin
   fresh();credit=0;submit();wait(ov);@(negedge clk);
   if(k==0)lease=0;else if(k==1)stop=1;else reset=1;
   #1;if(ov||!cancel)$fatal(1,"cancel exposed output %0d",k);
   repeat(3)tick();if(busy||ov||(k==0&&!fault))$fatal(1,"cancel not terminal");checks++;
  end
  // Fresh reset after fault recovers; old response is already drained by fixture.
  fresh();submit();wait(done);tick();if(fault||accepted!=16)$fatal(1,"fresh failed");checks++;
  $display("PASS WAIT216 GUARDS checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
