// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module plan196_boundary_tb;
 reg hc=0,nc=0,nrun=1,reset=1,stop=0,lease=1;
 always #3 hc=!hc;always #23 if(nrun)nc=!nc;
 reg wv=0,seal=0,ready=0,done=0;reg [7:0] wd=0;reg [5:0] len=0;reg [15:0] crc=0;
 wire wr,idle,fault,pv,ev;wire [1:0] kind;wire [15:0] gen,eg;
 wire [9:0] slot;wire [12:0] tag;wire [47:0] rows;wire [7:0] mask,am;wire [103:0] ats;
 nes_plan_stream196 dut(.host_clk(hc),.nes_clk(nc),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.seal(seal),.seal_length(len),.seal_crc(crc),.host_idle(idle),.fault(fault),
 .lease_valid(lease),.lease_generation(16'hffff),.plan_valid(pv),.plan_ready(ready),.tile_done(done),
 .plan_kind(kind),.plan_generation(gen),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(ats),
 .end_valid(ev),.end_ready(ready),.end_generation(eg));
 reg [7:0] b[0:31];integer size=16,i,j,k,f,r,v,c,checks=0;reg [15:0] cc;
 reg [208:0] saved;
 task nt;begin @(posedge nc);#1;end endtask
 task recover;begin
  stop=1;wv=0;seal=0;ready=0;done=0;lease=1;nrun=1;repeat(3)nt();stop=0;
  wait(idle);repeat(3)nt();if(fault||pv||ev)$fatal(1,"restart stale");
 end endtask
 task send(input integer corrupt,input integer length_delta);
  begin wait(idle);cc=16'hffff;
   for(i=0;i<size;i=i+1)begin
    @(negedge hc);wv=1;wd=b[i];if(!wr)$fatal(1,"write credit");
    cc=cc^{b[i],8'd0};for(j=0;j<8;j=j+1)cc=cc[15]?(cc<<1)^16'h1021:cc<<1;
   end
   @(negedge hc);wv=0;len=6'(size+length_delta);crc=cc^16'(corrupt);seal=1;
   @(negedge hc);seal=0;
  end
 endtask
 task complete;begin
  wait(pv);@(negedge nc);ready=1;nt();@(negedge nc);ready=0;
  repeat(3)nt();done=1;nt();@(negedge nc);done=0;checks++;
 end endtask
 initial begin
  repeat(5)nt();reset=0;wait(idle);
  f=$fopen("boundary.wire","r");if(!f)$fatal(1,"boundary missing");
  for(k=0;k<256;k=k+1)begin
   r=$fscanf(f,"%h",size);if(r!=1)$fatal(1,"length");
   for(i=0;i<size;i=i+1)begin r=$fscanf(f,"%h",v);b[i]=8'(v);end
   r=$fscanf(f,"%h",c);send(0,0);if(crc!==16'(c))$fatal(1,"independent CRC");
   wait(pv);#1;
   if(kind!=0||gen!=65535||slot!=1023||tag!=8191||mask!=255||am!=k)$fatal(1,"decoded header");
   for(i=0;i<16;i=i+1)if(rows[i*3+:3]!==3'((i*5)&7))$fatal(1,"row packing");
   for(i=0;i<8;i=i+1)if(ats[i*13+:13]!==13'(k&(1<<i)?8191-i:0))$fatal(1,"alternate tag packing");
   complete();
  end
  $fclose(f);
  // RAM may hold the NEXT plan while current fields remain owned by tile191.
  size=16;for(i=0;i<32;i=i+1)b[i]=0;
  b[0]=0;b[2]=255;b[3]=255;b[4]=1;b[8]=255;b[15]=1;
  send(0,0);wait(pv);saved={kind,gen,slot,tag,rows,mask,am,ats};
  @(negedge nc);ready=1;nt();@(negedge nc);ready=0;
  b[4]=2;send(0,0);repeat(50)nt();
  if({kind,gen,slot,tag,rows,mask,am,ats}!==saved||pv||ev)$fatal(1,"next RAM write changed running plan");
  done=1;nt();@(negedge nc);done=0;wait(pv);if(slot!=2)$fatal(1,"queued plan lost");complete();checks++;
  // All malformed transfers must be rejected BEFORE exposing plan/end.
  for(k=0;k<12;k=k+1)begin
   recover();size=16;for(i=0;i<32;i=i+1)b[i]=0;
   b[0]=0;b[2]=255;b[3]=255;b[4]=1;b[8]=255;b[15]=1;
   case(k)
    0:b[0]=4;1:b[15]=2;2:b[5]=4;3:b[7]=32;4:b[8]=0;
    5:begin b[0]=1;b[8]=0;end
    6:b[2]=254;7:b[1]=1;
    8:begin b[1]=1;size=18;b[17]=32;end
    9:b[0]=3;
   endcase
   send(k==10?1:0,k==11?2:0);
   for(i=0;i<150&&!fault;i=i+1)begin nt();if(pv||ev)$fatal(1,"invalid exposed");end
   if(!fault)$fatal(1,"not rejected %d",k);checks++;
  end
  // STOP with the NES clock paused cancels valid immediately; no old packet
  // may cross after local reset release or appear as a new generation.
  recover();b[0]=0;b[1]=0;b[2]=255;b[3]=255;b[4]=1;b[5]=0;b[7]=0;b[8]=255;b[15]=1;size=16;
  send(0,0);wait(pv);@(negedge nc);nrun=0;stop=1;#1;if(pv||ev||wr)$fatal(1,"paused cancel");checks++;
  recover();@(negedge hc);wv=1;wd=8'hab;@(negedge hc);wv=0;recover();checks++;
  // END is canonical generation only and never enters the tile engine.
  for(i=0;i<32;i=i+1)b[i]=0;b[0]=3;b[2]=255;b[3]=255;b[15]=1;send(0,0);wait(ev);
  if(pv||eg!=65535)$fatal(1,"END contract");ready=1;nt();ready=0;repeat(4)nt();checks++;
  $display("PASS PLAN196BOUNDARY checks=%0d",checks);$finish;
 end
 initial begin #20000000;$fatal(1,"timeout");end
endmodule
