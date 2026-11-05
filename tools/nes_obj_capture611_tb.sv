// SPDX-License-Identifier: MIT
module nes_obj_capture611_tb;
 reg clk=0; always #5 clk=~clk;
 reg reset=1,stop=0,immutable=1,start=0,seal=0,release_bank=0,sample=0,query=0;
 reg [15:0] capture_gen=0,release_gen=0,query_gen=0;
 reg [16:0] sample_address=0,query_address=0;
 reg [7:0] sample_data=0;
 wire start_ready,sample_ready,query_ready,response,hit;
 wire [7:0] data;
 nes_obj_capture611 dut(.*);
 task tick; begin @(posedge clk); #1; end endtask
 task launch(input integer g);begin
  capture_gen=g; #1;
  for(integer w=0;!start_ready&&w<300;w=w+1)tick;
  if(!start_ready)$fatal(1,"bank busy %d",g);
  start=1;tick;start=0;
 end endtask
 task finish_capture;begin seal=1;tick;seal=0;end endtask
 task ask(input integer g,a,v,ok);begin
  query_gen=g;query_address=a;query=1;tick;query=0;
  if(!response||hit!==ok[0]||(ok&&data!==v[7:0]))$fatal(1,"read %d %h",g,a);
 end endtask
 task release_g(input integer g);begin release_bank=1;release_gen=g;tick;release_bank=0;end endtask
 task put(input integer a,v);begin
  sample=1;sample_address=a;sample_data=v;#1;
  if(!sample_ready)$fatal(1,"sample");tick;sample=0;tick;
 end endtask
 integer f,rc,op,k,a,v,ok,g=904,queries=0,hits=0,fills=0,conc=0;
 integer keep_addr,keep_v,old_addr,old_v,old_gen;
 reg kept=0,previous=0,closed=0;
 initial begin
  tick;reset=0;repeat(2)tick;
  // Abort an uncommitted byte and reject an occupied bank and wrong-generation release.
  launch(1);sample=1;sample_address=31;sample_data=84;tick;sample=0;stop=1;tick;stop=0;
  repeat(2)tick;ask(1,31,84,0);launch(3);finish_capture;ask(3,31,84,0);release_g(3);
  launch(5);put(31,84);finish_capture;release_g(3);ask(5,31,84,1);
  capture_gen=7;#1;if(start_ready)$fatal(1,"reclaim");ask(7,31,84,0);
  ask(5,31,84,1);stop=1;#1;if(hit||response)$fatal(1,"STOP");
  stop=0;#1;if(hit||response||query_ready)$fatal(1,"short STOP");
  repeat(2)tick;ask(5,31,84,0);
  // Losing immutable identity and a too-early sample must both fall back.
  launch(6);put(42,99);finish_capture;immutable=0;tick;immutable=1;repeat(2)tick;ask(6,42,99,0);
  launch(8);sample=1;sample_address=42;sample_data=99;tick;
  // Holding a second sample into its pending commit is rejected.
  tick;sample=0;tick;finish_capture;ask(8,42,99,0);release_g(8);
  f=$fopen("stim.tsv","r");if(!f)$fatal(1,"fixture");
  while(!$feof(f))begin
   rc=$fscanf(f,"%d %d %h %h %d\n",op,k,a,v,ok);
   if(rc==5)begin
    if(op==0)begin
     if(g>=905&&!closed)finish_capture;
     if(g>=906)release_g(g-1);
     old_addr=keep_addr;old_v=keep_v;old_gen=g;previous=kept;kept=0;
     g=g+1;closed=0;launch(g);
    end else if(op==1&&k==1)begin
     if(previous)begin
      sample=1;sample_address=a;sample_data=v;
      query=1;query_gen=old_gen;query_address=old_addr;#1;
      if(query_ready||!sample_ready)$fatal(1,"capture priority");
      tick;if(response)$fatal(1,"early query");sample=0;#1;
      if(!query_ready)$fatal(1,"port not returned at commit");
      tick;query=0;if(!hit||data!==old_v[7:0])$fatal(1,"overlap");
      conc=conc+1;
     end else put(a,v);
     fills=fills+1;
    end else if(op==2)begin
     if(!closed)begin finish_capture;closed=1;end
     if(k==1)begin
      ask(g,a,v,ok);queries=queries+1;hits=hits+ok;
      if(ok)begin kept=1;keep_addr=a;keep_v=v;end
     end
    end
   end
  end
  if(g!=957||conc==0||queries==0)$fatal(1,"coverage");
  $display("PASS611 fills=%0d queries=%0d hits=%0d concurrent=%0d",fills,queries,hits,conc);
  $finish;
 end
endmodule
