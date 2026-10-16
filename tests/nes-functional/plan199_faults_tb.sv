// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module plan199_faults_tb;
 reg host_clk=0,nc=0,nrun=1,reset=1,stop=0,source_fault=0;
 always #5.952 host_clk=!host_clk;always #23.280423 if(nrun)nc=!nc;
 `include "spi199_bus.svh"
 wire idle,wr,wv,seal,pf,sf,pv,ev;wire [7:0] wd;wire [9:0] len;wire [4:0] number;wire [15:0] crc;
 reg ready=0,done=0,auto_run=0;integer seen=0,delay_done=0;wire [9:0] slot;reg cr=0,es=0;reg [31:0] token=32'h12345678;
 wire [1:0] kind;wire [15:0] gen;wire [12:0] tag;wire [47:0] rows;wire [7:0] mask,am;
 nes_plan_spi199 spi(.clk(host_clk),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(pf||source_fault),
 .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.selected(selected197),.miso(miso197),.fault(sf),
 .plan_idle(idle),.plan_ready(wr),.plan_write(wv),.plan_data(wd),.plan_seal(seal),.plan_length(len),.plan_plans(number),.plan_crc(crc),
 .chunk_ready(cr),.chunk_kind(1'b1),.chunk_length(12'd2048),.chunk_slot(10'd64),.chunk_generation(16'hffff),.chunk_token(token),.end_sealed(es));
 nes_plan_batch199 plan(.host_clk(host_clk),.nes_clk(nc),.reset(reset),.active(1'b1),.stop(stop),.source_fault(sf),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.seal(seal),.seal_length(len),.seal_plans(number),.seal_crc(crc),.host_idle(idle),.fault(pf),
 .lease_valid(1'b1),.lease_generation(16'hffff),.plan_valid(pv),.plan_ready(ready),.tile_done(done),
 .plan_kind(kind),.plan_generation(gen),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(),
 .end_valid(ev),.end_ready(1'b0),.end_generation());
 reg [7:0] b[0:519],u,fc;reg [15:0] pc;integer i,j,k,n,checks=0,published=0;
 always @(posedge nc)begin
  if(pv||ev)published<=published+1;
  if(auto_run)begin
   ready<=1;done<=0;
   if(pv&&ready)begin
    if(slot!=1+seen%16)$fatal(1,"bank overwrite/order slot=%d seen=%d",slot,seen);
    seen<=seen+1;delay_done<=3;
   end
   if(delay_done>0)begin delay_done<=delay_done-1;if(delay_done==1)done<=1;end
  end
 end
 task recover;begin
  auto_run=0;stop=1;ss197=1;sck197=0;ready=0;done=0;nrun=1;source_fault=0;#1000;stop=0;#2000;
  if(sf||pf||pv||ev||!idle)$fatal(1,"restart");published=0;
 end endtask
 task recalc;begin
  pc=16'hffff;for(i=4;i<n-4;i=i+1)begin pc=pc^{b[i],8'd0};for(j=0;j<8;j=j+1)pc=pc[15]?(pc<<1)^16'h1021:pc<<1;end
  b[n-4]=pc[15:8];b[n-3]=pc[7:0];fc=0;
  for(i=0;i<n-2;i=i+1)fc=crc8_197(fc,b[i]);b[n-2]=fc;b[n-1]=8'ha5;
 end endtask
 task prepare(input integer size);begin
  for(i=0;i<520;i=i+1)b[i]=0;n=size+8;b[0]=8'he9;b[1]=8'(size);b[2]=8'(size>>8);b[3]=1;
  b[4]=0;b[6]=255;b[7]=255;b[8]=1;b[12]=255;b[19]=1;
  if(size==32)begin b[5]=255;for(i=20;i<36;i=i+2)b[i]=1;end
  recalc();
 end endtask
 task send;begin begin197();for(k=0;k<n;k=k+1)byte197(b[k],u);end197();end endtask
 initial begin
  #1000;reset=0;#2000;
  prepare(32);send();wait(pv);status197();if(sf||pf||{rx197[4],rx197[5]}!=1)$fatal(1,"max plan");checks++;
  recover();
  // Unrecognized command does not claim MISO or alter transport state.
  begin197();byte197(8'h70,u);#100;if(selected197)$fatal(1,"command overlap");end197();
  if(sf||pf||!idle)$fatal(1,"unrelated command");checks++;
  cr=1;begin197();byte197(8'he8,u);token=32'habcdef01;
  for(i=1;i<20;i=i+1)byte197(0,rx197[i]);end197();
  if({rx197[17],rx197[16],rx197[15],rx197[14]}!=32'h12345678||{rx197[11],rx197[10]}!=2048)$fatal(1,"snapshot moved");checks++;
  cr=0;es=1;#100;es=0;status197();status197();if(!rx197[3][1])$fatal(1,"lost END pulse");checks++;
  recover();source_fault=1;#100;source_fault=0;status197();if(!sf||!rx197[3][7])$fatal(1,"fault not sticky");checks++;
  recover();prepare(16);send();wait(pv);nrun=0;stop=1;#1;if(pv||ev||wr)$fatal(1,"paused STOP");checks++;recover();
  // With paused decoder, two complete banks fit; third must be refused.
  nrun=0;prepare(16);send();prepare(16);send();#2000;if(idle)$fatal(1,"no backpressure");prepare(16);send();
  if(!sf)$fatal(1,"busy write admitted");checks++;recover();
  $display("PASS BATCH199FAULT positive=%0d",checks);
  run_bad();queue_check();short_check();$display("PASS BATCH199FAULT checks=%0d",checks);$finish;
 end
 integer mode;
 task run_bad;begin
  for(mode=0;mode<13;mode=mode+1)begin
   prepare(16);
   case(mode)
    0:n=10;
    1:begin b[20]=b[20]^1;fc=0;for(i=0;i<22;i=i+1)fc=crc8_197(fc,b[i]);b[22]=fc;end
    2:b[22]=b[22]^1;
    3:b[23]=0;
    4:b[1]=15;
    5:b[2]=3;
    6:begin n=25;b[24]=0;end
    7:begin b[19]=2;recalc();end
    8:n=1;
    9:begin b[3]=0;recalc();end
    10:begin b[3]=17;recalc();end
    11:begin b[3]=2;recalc();end // Claimed extra plan with no bytes.
    12:begin prepare(32);b[5]=0;recalc();end // Trailing bytes with one16B plan.
   endcase
   send();#10000;if(!sf||pv||ev||published)$fatal(1,"bad admitted mode=%d",mode);checks++;recover();
  end
  // Partial bit at end of otherwise valid command cannot publish.
  prepare(16);begin197();for(k=0;k<n;k=k+1)byte197(b[k],u);
  #62.5;sck197=1;#62.5;sck197=0;end197();#10000;
  if(!sf||published)$fatal(1,"partial bit");checks++;recover();
 end endtask
 task short_prepare(input integer kind0);integer size;begin
  size=kind0>=2?3:kind0==1?8:7;
  for(i=0;i<520;i=i+1)b[i]=0;n=size+8;b[0]=8'he9;b[1]=8'(size);b[3]=1;
  b[4]=8'h80|8'(kind0);b[5]=255;b[6]=255;
  if(kind0<2)begin
   b[7]=kind0==1?127:255;b[8]=kind0==1?0:3;b[9]=255;b[10]=31;
   if(kind0==1)b[11]=8'ha5;
  end
  recalc();
 end endtask
 task short_check;integer c,f;reg [47:0] identity;begin
  identity=0;for(f=0;f<16;f=f+1)identity[f*3+:3]=3'(f/2);
  for(c=0;c<4;c=c+1)begin
   recover();short_prepare(c);send();if(c==3)wait(ev);else wait(pv);
   if(sf||pf||kind!=c||gen!=65535||am!=0)$fatal(1,"short decode header");
   if(c<2)begin
    if(tag!=8191||slot!=(c==1?127:1023)||rows!=identity||mask!=(c==1?165:255))$fatal(1,"short decode fields");
   end else if(tag||slot||rows||mask)$fatal(1,"short control fields");
   checks++;
  end
  for(c=0;c<10;c=c+1)begin
   recover();short_prepare((c==5||c==6)?1:0);
   case(c)
    0:b[4]=8'h84;
    1:b[5]=254;
    2:begin b[7]=0;b[8]=0;end
    3:b[8]=4;
    4:b[10]=32;
    5:b[7]=128;
    6:b[11]=0;
    7:begin n=14;b[1]=6;end
    8:begin n=16;b[1]=8;b[11]=0;end
    9:begin n=14;b[1]=6;b[3]=2;b[4]=8'h83;b[7]=8'h82;b[8]=255;b[9]=255;end
   endcase
   recalc();send();#10000;if(!sf||pv||ev||published)$fatal(1,"invalid short admitted %d",c);checks++;
  end
  recover();
 end endtask
 task group;integer row,at;begin
  for(i=0;i<520;i=i+1)b[i]=0;n=520;b[0]=8'he9;b[1]=0;b[2]=2;b[3]=16;
  for(row=0;row<16;row=row+1)begin
   at=4+row*32;b[at]=0;b[at+1]=255;b[at+2]=255;b[at+3]=255;b[at+4]=8'(row+1);b[at+8]=255;b[at+15]=1;
   for(i=16;i<32;i=i+2)b[at+i]=8'(row);
  end
  recalc();
 end endtask
 task queue_check;integer batch;begin
  recover();seen=0;nrun=0;group();send();group();send();
  if(idle||published)$fatal(1,"two banks not held");
  nrun=1;auto_run=1;
  for(batch=2;batch<8;batch=batch+1)begin wait(idle);group();send();end
  wait(seen==128);#10000;if(sf||pf)$fatal(1,"queue fault");checks++;
  recover();nrun=0;group();send();group();send();stop=1;#1000;
  recover();#10000;if(pv||ev||published)$fatal(1,"cancel leaked queued plans");checks++;
 end endtask
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
