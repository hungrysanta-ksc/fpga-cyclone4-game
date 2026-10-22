`timescale 1ns/1ps
module mux258_tb;
 parameter SHARED=1,GUARD=0;
 reg nc=0,hc=0;always #22.727 nc=~nc;always #5 hc=~hc;
 reg reset=1,cancel=0,iv=0;wire ir;reg [31:0] serial=1;reg [15:0] gen=1;reg bank=0;
 reg ss=1,sck=0,mosi=0;wire miso;
 reg [23:0] address=0;reg rn=1,wn=1;reg [7:0] din=0;wire [7:0] dout;wire valid;
 reg tv=0;wire tr;reg [7:0] td;reg [4:0] ti;reg [5:0] tl=16;reg [1:0] tk=0;reg [9:0] ts=0;reg ev=0;wire er;
 wire rv,rdone;wire [11:0] rf,rc;reg ready=1,sealed=0;wire ack,retired,staged,receipt,fault,ordinary;
 wire [31:0] nt;integer receipt_delay=0,receipts=0,acks=0,ordinary_count=0,dma_bytes=0;
 nes_mux258 #(.SHARED(SHARED),.INITIAL_TOKEN(GUARD==12?32'hfffffffe:32'd1)) dut(
 .nes_clk(nc),.host_clk(hc),.reset(reset),.cancel(cancel),.identity_valid(iv),.identity_ready(ir),.serial(serial),.generation(gen),.bank(bank),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(miso),.address(address),.read_n(rn),.write_n(wn),.data_in(din),.data_out(dout),.bus_valid(valid),
 .tile_valid(tv),.tile_ready(tr),.tile_data(td),.tile_index(ti),.tile_length(tl),.tile_kind(tk),.tile_slot(ts),.tile_generation(gen),
 .end_valid(ev),.end_ready(er),.end_generation(gen),.range_valid(rv),.range_ready(ready),.range_first(rf),.range_count(rc),.range_dma_done(rdone),
 .sealed(sealed),.core_idle(1'b1),.display_ack(ack),.retired(retired),.staged(staged),.receipt_committed(receipt),.fault(fault),.ordinary_ready(ordinary),.next_token(nt));
 // Bounded receipt-service endpoint for schedule comparison only. The actual
 // core/semantic seal remains covered by the separate257/258 Mesen join.
 always @(posedge nc)begin
  if(reset||cancel)begin ready<=1;receipt_delay<=0;end
  else begin
   if(rv&&ready)begin ready<=0;receipt_delay<=8;end
   if(receipt_delay>0)begin receipt_delay<=receipt_delay-1;if(receipt_delay==1)begin ready<=1;receipts++;end end
   if(ack)acks++;
  end
 end
 integer ticks=0,fd,map_wait_tile=0,ordinary_hold=0,ack_check=0;
 reg [31:0] oldtoken=0;reg [4:0] oldstate=0;reg [1:0] oldowner=0;reg oldstaged=0;
 always @(posedge hc)begin
  ticks++;
  if(!reset&&!cancel)begin
   if(!GUARD&&fault)$fatal(1,"fault state=%0d owner=%0d q=%0d tile=%0d",dut.state,dut.owner,dut.qfault,dut.tfault);
   if(dut.qretire&&(dut.ack_write||dut.ack_publish||dut.queue.checking))$fatal(1,"two retire owners");
   if(dut.queue.checking&&ordinary)$fatal(1,"head visible during checker");
   if(dut.state==dut.OPEN&&dut.owner==dut.TILE)map_wait_tile++;
   if(ordinary)ordinary_hold++;
   if(dut.queue.checking)ack_check++;
   if(staged&&(!oldstaged||oldtoken!=dut.chunk_token))$fwrite(fd,"stage,%0d,%0d,%0d\n",ticks,dut.owner,dut.chunk_token);
   if(dut.consume)$fwrite(fd,"consume,%0d,%0d,%0d\n",ticks,dut.owner,dut.chunk_token);
   if(dut.qretire||dut.qdone)$fwrite(fd,"retire,%0d,%0d,%0d\n",ticks,dut.qretire,dut.queue.retired);
  end
  oldstate<=dut.state;oldowner<=dut.owner;oldstaged<=staged;oldtoken<=dut.chunk_token;
 end
 function automatic [15:0] crc16(input [15:0] prev,input [7:0] b);
 reg [15:0] c;begin c=prev^{b,8'd0};for(integer k=0;k<8;k++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;end endfunction
 reg [7:0] packet[0:99];reg [7:0] val;
 task spi_byte(input [7:0] b);begin for(integer k=7;k>=0;k--)begin mosi=b[k];#190;sck=1;#190;sck=0;end end endtask
 task send_packet(input integer op,seq,input [31:0] tok,input integer seed);
 integer n;reg [15:0] crc;begin
  n=op==9?84:16;
  for(integer i=0;i<100;i++)packet[i]=0;
  packet[0]=op;packet[1]=bank;packet[2]=seq;packet[3]=seq>>8;
  for(integer i=0;i<4;i++)packet[4+i]=serial>>(8*i);
  packet[8]=gen;packet[9]=gen>>8;
  if(op==9)begin
   packet[12]=68;packet[14]=64;
   for(integer i=0;i<4;i++)packet[16+i]=tok>>(8*i);
   for(integer i=0;i<64;i++)packet[20+i]=(seed+i)&255;
  end
  @(negedge hc);ss=0;crc=crc16(16'hffff,8'he1);spi_byte(8'he1);
  for(integer i=0;i<n;i++)begin spi_byte(packet[i]);crc=crc16(crc,packet[i]);end
  spi_byte(crc[15:8]);spi_byte(crc[7:0]);#190;ss=1;repeat(8)@(negedge hc);
 end endtask
 task rd(input [23:0] a,output reg [7:0] b);begin
  @(negedge hc);address=a;rn=0;#200;if(!valid)$fatal(1,"invalid read %h state%0d",a,dut.state);b=dout;rn=1;#200;
 end endtask
 task wr(input [23:0] a,input [7:0] b);begin @(negedge hc);address=a;din=b;wn=0;#200;wn=1;#200;end endtask
 task write_token(input [31:0] tok);begin for(integer i=0;i<4;i++)wr(24'h00604c+i,tok>>(i*8));end endtask
 task admit;begin wait(ir);@(negedge nc);iv=1;@(negedge nc);iv=0;repeat(20)@(negedge hc);end endtask
 task tile(input integer slot,seed);begin
  for(integer i=0;i<16;i++)begin wait(tr);@(negedge nc);tv=1;ti=i;ts=slot;td=seed+i;@(negedge nc);tv=0;end
 end endtask
 task end_tiles;begin wait(er);@(negedge nc);ev=1;@(negedge nc);ev=0;end endtask
 task ordinary_ack(input integer seq,bad);
 reg [7:0] h[0:15];begin
  wait(ordinary);for(integer i=0;i<16;i++)rd(24'h400000+i,h[i]);
  if(h[0]!=2||h[1]!=bank||{h[3],h[2]}!=seq||{h[9],h[8]}!=gen)$fatal(1,"normal packet mismatch");
  wr(24'h006010,0);wr(24'h006011,2);
  for(integer i=2;i<10;i++)wr(24'h006010+i,h[i]^(bad&&i==2));
  wr(24'h00601a,8'h65);wr(24'h00601b,8'h9a);wr(24'h00601c,8'ha5);
  if(!bad)begin wait(dut.qdone);ordinary_count++;@(negedge hc);end
 end endtask
 task dma(input integer n,seed,input [31:0] tok,input integer do_consume);begin
  wait(staged);
  rd(24'h006041,val);if(val[2]!=bank||val[1]!=(dut.owner==dut.MAP))$fatal(1,"bank/kind mismatch");
  rd(24'h006046,val);if(val!=gen[7:0])$fatal(1,"generation low mismatch");
  rd(24'h006047,val);if(val!=gen[15:8])$fatal(1,"generation high mismatch");
  for(integer j=0;j<4;j++)begin rd(24'h006048+j,val);if(val!==((tok>>(8*j))&255))$fatal(1,"token mismatch %d/%d",val,tok);end
  for(integer i=0;i<n;i++)begin rd(24'h400800+i,val);if(val!==((seed+i)&255))$fatal(1,"DMA byte %0d got%0d want%0d",i,val,(seed+i)&255);dma_bytes++;end
  if(do_consume)begin write_token(tok);wr(24'h006050,8'ha5);end
 end endtask
 task final_ack(input [31:0] tok);begin
  wait(receipt);wait(dut.state==dut.IDLE);sealed=1;repeat(10)@(negedge hc);
  for(integer i=0;i<4;i++)begin rd(24'h006048+i,val);if(val!==((tok>>(8*i))&255))$fatal(1,"retired token not held for final ACK");end
  write_token(tok);wr(24'h006058,8'h5a);wait(retired);sealed=0;repeat(10)@(negedge hc);
 end endtask
 task stopped;reg [31:0] prior_token;begin
  prior_token=nt;@(negedge hc);cancel=1;tv=0;ev=0;ss=1;rn=1;wn=1;repeat(12)@(negedge hc);
  if(staged||rv||ack||ordinary||retired||nt!=prior_token)$fatal(1,"STOP visibility/token");
  cancel=0;serial++;gen++;bank=!bank;repeat(12)@(negedge hc);admit();
 end endtask
 task rejected;begin
  wait(fault);repeat(20)@(negedge hc);
  if(valid||ordinary||staged||ack)$fatal(1,"fault exposes output");
  $display("PASS MUX258 GUARD=%0d SHARED=%0d",GUARD,SHARED);$finish;
 end endtask
 initial begin
  fd=$fopen("events.csv","w");repeat(8)@(negedge hc);reset=0;repeat(12)@(negedge hc);admit();
  if(GUARD==15)begin
   send_packet(9,0,1,40);wait(staged);tile(0,90);
   fork
    end_tiles();
    begin
     repeat(100)@(negedge hc);
     if(dut.owner!=dut.MAP||tr||dut.tiles.word_ready)$fatal(1,"tile bypassed map lease");
     dma(64,40,1,1);wait(receipt);dma(16,90,2,1);wait(dut.owner==dut.NONE);final_ack(1);
     if(fault||acks!=1)$fatal(1,"map-to-tile ownership");$display("PASS MUX258 GUARD=15 SHARED=%0d",SHARED);$finish;
    end
   join
  end
  if(GUARD==16)begin
   tile(0,10);tile(2,30);end_tiles();wait(dut.tiles.end_sealed);repeat(10)@(negedge hc);
   if(nt!=3)$fatal(1,"two tile tokens not allocated");
   dma(8,10,1,0);stopped();send_packet(9,0,3,60);dma(64,60,3,0);write_token(2);wr(24'h006050,8'ha5);rejected();
  end
  if(GUARD==13)begin
   send_packet(9,0,1,40);dma(64,40,1,1);wait(receipt);
   serial=2;gen=2;bank=1;@(negedge nc);iv=1;repeat(20)@(negedge nc);
   if(ir||dut.identity[31:0]!=1||fault)$fatal(1,"early identity admitted");
   iv=0;final_ack(1);admit();send_packet(9,0,2,60);dma(64,60,2,1);final_ack(2);
   if(fault||acks!=2)$fatal(1,"identity retirement ordering");$display("PASS MUX258 GUARD=13 SHARED=%0d",SHARED);$finish;
  end
  if(GUARD==14)begin
   cancel=1;repeat(12)@(negedge hc);cancel=0;serial=32'hffffffff;admit();
   cancel=1;repeat(12)@(negedge hc);cancel=0;serial=0;admit();rejected();
  end
  if(GUARD==12)begin send_packet(9,0,32'hfffffffe,80);dma(64,80,32'hfffffffe,1);wait(receipt);send_packet(9,1,32'hffffffff,90);rejected();end
  if(GUARD==3)begin stopped();cancel=1;repeat(8)@(negedge hc);cancel=0;serial--;admit();rejected();end
  if(GUARD==10)begin
   wait(tr);@(negedge nc);tv=1;ti=0;td=55;@(negedge nc);tv=0;stopped();
   tile(0,90);end_tiles();dma(16,90,1,1);repeat(20)@(negedge hc);
   if(fault||staged)$fatal(1,"partial tile restart");$display("PASS MUX258 GUARD=10 SHARED=%0d",SHARED);$finish;
  end
  if(GUARD==6||GUARD==9)begin
   send_packet(2,0,0,0);
   if(GUARD==6)begin ordinary_ack(0,1);rejected();end
   else begin
    fork ordinary_ack(0,0);begin wait(dut.queue.checking);stopped();send_packet(9,0,1,55);dma(64,55,1,1);wait(receipt);
     if(fault||dut.queue.retired!=1)$fatal(1,"checker STOP leaked retire");$display("PASS MUX258 GUARD=9 SHARED=%0d",SHARED);$finish;end join
   end
  end
  if(GUARD!=0)begin
   if(GUARD==7)begin
    fork send_packet(9,0,1,40);begin wait(dut.state==dut.PUT&&dut.at==7);stopped();send_packet(9,0,2,60);dma(64,60,2,1);wait(receipt);
      if(fault)$fatal(1,"partial fill restart");$display("PASS MUX258 GUARD=7 SHARED=%0d",SHARED);$finish;end join
   end
   send_packet(9,0,1,40);wait(staged);
   if(GUARD==1)begin dma(64,40,1,0);write_token(0);wr(24'h006050,8'ha5);rejected();end
   if(GUARD==2)begin dma(64,40,1,1);final_ack(1);serial++;gen++;bank=1;admit();send_packet(9,0,1,50);rejected();end
   if(GUARD==4)begin wr(24'h006010,0);rejected();end
   if(GUARD==5)begin dma(8,40,1,0);write_token(1);wr(24'h006050,8'ha5);rejected();end
   if(GUARD==8)begin dma(8,40,1,0);stopped();send_packet(9,0,2,70);dma(64,70,2,0);write_token(1);wr(24'h006050,8'ha5);rejected();end
   if(GUARD==11)begin dma(64,40,1,1);wait(receipt);write_token(1);wr(24'h006050,8'ha5);rejected();end
  end
  // Two non-contiguous tiles force two real206 chunks and both physical banks.
  tile(0,16);tile(2,48);end_tiles();
  send_packet(2,0,0,0);send_packet(9,1,3,80);send_packet(2,2,0,0);send_packet(9,3,4,144);
  repeat(200)@(negedge hc);
  if(dut.queue.accepted!=4||dut.queue.retired!=0||!ordinary)$fatal(1,"head/credit bypass");
  ordinary_ack(0,0);repeat(100)@(negedge hc);
  if(dut.queue.retired!=1||dut.owner!=dut.TILE||dut.state!=dut.OPEN)$fatal(1,"typed bypassed tile lease");
  dma(16,16,1,1);dma(16,48,2,1);dma(64,80,3,1);wait(receipt);
  ordinary_ack(2,0);dma(64,144,4,1);final_ack(4);
  if(dut.queue.retired!=4)$fatal(1,"queue retire count");
  // Reuse both bank identities and the same aperture addresses without reset.
  for(integer frame=2;frame<=3;frame++)begin
   serial=frame;gen=frame;bank=(frame==2);admit();send_packet(9,0,frame+3,frame*40);dma(64,frame*40,frame+3,1);final_ack(frame+3);
  end
  if(fault||receipts!=4||acks!=3||ordinary_count!=2||nt!=7||dma_bytes!=288)$fatal(1,"final totals r%0d a%0d o%0d token%0d bytes%0d",receipts,acks,ordinary_count,nt,dma_bytes);
  $fclose(fd);$display("PASS MUX258 SHARED=%0d ticks=%0d bytes=%0d receipts=%0d ordinary=%0d mapwait=%0d ordinaryhold=%0d ackcheck=%0d",SHARED,ticks,dma_bytes,receipts,ordinary_count,map_wait_tile,ordinary_hold,ack_check);$finish;
 end
 initial begin #10000000;$fatal(1,"watchdog state%0d owner%0d fault%0d tiles%0d",dut.state,dut.owner,fault,dut.tiles.state);end
endmodule
