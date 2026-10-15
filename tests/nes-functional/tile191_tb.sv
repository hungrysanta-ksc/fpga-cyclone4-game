// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tile191_tb;
 parameter integer SCENE=0;
 reg clk=0,reset=1,stop=0,lease=1;
 always #5.952 clk=!clk;
 reg pv=0;wire pr;reg [1:0] kind;reg [15:0] gen;reg [9:0] slot;reg [12:0] tag;
 reg [47:0] rows;reg [7:0] mask,am;reg [103:0] ats;
 wire req,cancel;wire [16:0] addr;wire [15:0] mg;
 reg response=0,error=0,pending=0;reg [16:0] ra=0;reg [15:0] rg=0;reg [7:0] rd=0;
 reg [7:0] memory[0:159],expected[0:32767];
 wire ov;wire [7:0] od;wire [4:0] oi;wire [5:0] length;wire [1:0] ok;
 wire [9:0] os;wire [15:0] og;wire busy,fault,done;
 integer cycle=0,delay=0,checked=0,reads=0,tiles=0,stall=0;
 wire ready=cycle%7!=0;
 wire out_ready=cycle%5!=0;
 nes_tile191 dut(.clk(clk),.reset(reset),.stop(stop),.lease_valid(lease),.lease_generation(16'(100+SCENE)),
  .plan_valid(pv),.plan_ready(pr),.plan_kind(kind),.plan_generation(gen),.plan_slot(slot),.plan_tag(tag),
  .plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(ats),
  .mem_idle(!pending&&!response),.mem_ready(ready),.mem_request(req),.mem_cancel(cancel),.mem_address(addr),.mem_generation(mg),
  .mem_response(response),.mem_error(error),.response_address(ra),.response_generation(rg),.response_data(rd),
  .out_valid(ov),.out_ready(out_ready),.out_data(od),.out_index(oi),.out_length(length),.out_kind(ok),.out_slot(os),.out_generation(og),
  .busy(busy),.fault(fault),.done(done));
 always @(posedge clk)begin
  cycle<=cycle+1;response<=0;
  if(cancel)begin pending<=0;response<=0;end
  else if(pending)begin
   if(delay==0)begin response<=1;pending<=0;end else delay<=delay-1;
  end else if(req&&ready)begin
   if(addr>=160)$fatal(1,"unsealed address");
   pending<=1;ra<=addr;rg<=mg;rd<=memory[addr];delay<=reads%5+1;reads<=reads+1;
  end
  if(ov&&!out_ready)stall<=stall+1;
  if(ov&&out_ready)begin
   if(od!==expected[checked]||ok!=kind||os!=slot||og!=gen||length!=(kind==1?32:16))
    $fatal(1,"output mismatch byte=%d got=%x expected=%x",checked,od,expected[checked]);
   checked<=checked+1;
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 integer f,n;reg [1023:0] filename;
 initial begin
  $sformat(filename,"scene%0d.mem",SCENE);$readmemh(filename,memory,0,159);
  $sformat(filename,"scene%0d.expected",SCENE);$readmemh(filename,expected);
  $sformat(filename,"scene%0d.rtl",SCENE);f=$fopen(filename,"r");if(!f)$fatal(1,"plans missing");
  repeat(5)tick();reset=0;tick();
  while(!$feof(f))begin
   @(negedge clk);n=$fscanf(f,"%h %h %h %h %h %h %h %h\n",kind,gen,slot,tag,mask,rows,am,ats);
   if(n==8)begin
    while(!pr)tick();@(negedge clk);pv=1;tick();@(negedge clk);pv=0;
    while(!done&&!fault)tick();if(fault)$fatal(1,"unexpected materializer fault");tiles=tiles+1;
   end else if(n!=-1&&n!=0)$fatal(1,"bad fixture");
  end
  $fclose(f);if(checked==0||stall==0)$fatal(1,"empty/stall coverage");
  $display("PASS TILE191 scene=%0d tiles=%0d bytes=%0d reads=%0d stalls=%0d cycles=%0d",SCENE,tiles,checked,reads,stall,cycle);$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
