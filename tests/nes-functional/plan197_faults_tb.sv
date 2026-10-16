// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module plan197_faults_tb;
 reg host_clk=0,nc=0,nrun=1,reset=1,stop=0,source_fault=0;
 always #5.952 host_clk=!host_clk;always #23.280423 if(nrun)nc=!nc;
 `include "spi197_bus.svh"
 wire idle,wr,wv,seal,pf,sf,pv,ev;wire [7:0] wd;wire [5:0] len;wire [15:0] crc;
 reg ready=0,done=0;reg cr=0,es=0;reg [31:0] token=32'h12345678;
 nes_plan_spi197 spi(.clk(host_clk),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(pf||source_fault),
 .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.selected(selected197),.miso(miso197),.fault(sf),
 .plan_idle(idle),.plan_ready(wr),.plan_write(wv),.plan_data(wd),.plan_seal(seal),.plan_length(len),.plan_crc(crc),
 .chunk_ready(cr),.chunk_kind(1'b1),.chunk_length(12'd2048),.chunk_slot(10'd64),.chunk_generation(16'hffff),.chunk_token(token),.end_sealed(es));
 nes_plan_stream196 plan(.host_clk(host_clk),.nes_clk(nc),.reset(reset),.active(1'b1),.stop(stop),.source_fault(sf),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.seal(seal),.seal_length(len),.seal_crc(crc),.host_idle(idle),.fault(pf),
 .lease_valid(1'b1),.lease_generation(16'hffff),.plan_valid(pv),.plan_ready(ready),.tile_done(done),
 .plan_kind(),.plan_generation(),.plan_slot(),.plan_tag(),.plan_rows(),.plan_mask(),.plan_alt_mask(),.plan_alt_tags(),
 .end_valid(ev),.end_ready(1'b0),.end_generation());
 reg [7:0] b[0:37],u,fc;reg [15:0] pc;integer i,j,k,n,checks=0,published=0;
 always @(posedge nc)if(pv||ev)published<=published+1;
 task recover;begin
  stop=1;ss197=1;sck197=0;ready=0;done=0;nrun=1;source_fault=0;#1000;stop=0;#2000;
  if(sf||pf||pv||ev||!idle)$fatal(1,"restart");published=0;
 end endtask
 task prepare(input integer size);begin
  for(i=0;i<38;i=i+1)b[i]=0;n=size+6;b[0]=8'he9;b[1]=8'(size);
  b[2]=0;b[4]=255;b[5]=255;b[6]=1;b[10]=255;b[17]=1;
  if(size==32)begin b[3]=255;for(i=18;i<34;i=i+2)b[i]=1;end
  pc=16'hffff;for(i=2;i<size+2;i=i+1)begin pc=pc^{b[i],8'd0};for(j=0;j<8;j=j+1)pc=pc[15]?(pc<<1)^16'h1021:pc<<1;end
  b[size+2]=pc[15:8];b[size+3]=pc[7:0];fc=0;
  for(i=0;i<size+4;i=i+1)fc=crc8_197(fc,b[i]);b[size+4]=fc;b[size+5]=8'ha5;
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
  // Fill decoder hold and next RAM slot, then violate credit.
  prepare(16);send();wait(pv);prepare(16);send();#2000;if(idle)$fatal(1,"no backpressure");prepare(16);send();
  if(!sf)$fatal(1,"busy write admitted");checks++;recover();
  $display("PASS SPI197FAULT positive=%0d",checks);
  run_bad();$display("PASS SPI197FAULT checks=%0d",checks);$finish;
 end
 integer mode;
 task run_bad;begin
  for(mode=0;mode<9;mode=mode+1)begin
   prepare(16);
   case(mode)
    0:n=10; // interrupted payload
    1:b[18]=b[18]^1; // payload CRC, fix framing CRC to reach196 check
    2:b[20]=b[20]^1;
    3:b[21]=0;
    4:b[1]=15;
    5:b[1]=34;
    6:begin n=23;b[22]=0;end
    7:b[17]=2; // version, both CRCs recomputed below
    8:n=1;
   endcase
   if(mode==7)begin
    pc=16'hffff;for(i=2;i<18;i=i+1)begin pc=pc^{b[i],8'd0};for(j=0;j<8;j=j+1)pc=pc[15]?(pc<<1)^16'h1021:pc<<1;end
    b[18]=pc[15:8];b[19]=pc[7:0];
   end
   if(mode==1||mode==7)begin fc=0;for(i=0;i<20;i=i+1)fc=crc8_197(fc,b[i]);b[20]=fc;end
   send();#10000;if(!sf||pv||ev||published)$fatal(1,"bad admitted mode=%d",mode);checks++;recover();
  end
  // Partial bit at end of otherwise valid command cannot publish.
  prepare(16);begin197();for(k=0;k<n;k=k+1)byte197(b[k],u);
  #62.5;sck197=1;#62.5;sck197=0;end197();#10000;
  if(!sf||published)$fatal(1,"partial bit");checks++;recover();
 end endtask
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
