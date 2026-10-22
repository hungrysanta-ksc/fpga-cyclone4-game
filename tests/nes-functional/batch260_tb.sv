`timescale 1ns/1ps
module batch260_tb;
 parameter SHARED=1,GUARD=0;
 reg nc=0,hc=0;always #22.727 nc=~nc;always #5 hc=~hc;
 reg reset=1,cancel=0,iv=0;wire ir;reg [31:0] serial=1;reg [15:0] gen=1;reg bank=0;
 reg ss=1,sck=0,mosi=0;wire miso;
 reg [23:0] address=0;reg rn=1,wn=1;reg [7:0] din=0;wire [7:0] dout;wire valid;
 reg tv=0;wire tr;reg [7:0] td;reg [4:0] ti;reg [5:0] tl=16;reg [1:0] tk=0;reg [9:0] ts=0;reg ev=0;wire er;
 wire rv,rdone;wire [11:0] rf,rc;reg ready=1,sealed=0,hold_receipt=0;wire ack,retired,staged,receipt,fault,ordinary;
 wire [31:0] nt;integer receipt_delay=0,receipts=0,acks=0,ordinary_count=0,dma_bytes=0;
 nes_output260 #(.SHARED(SHARED),.INITIAL_TOKEN((GUARD==12||GUARD==33)?32'hfffffffe:32'd1)) dut(
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
   if(receipt_delay>0&&!(receipt_delay==1&&hold_receipt))begin receipt_delay<=receipt_delay-1;if(receipt_delay==1)begin ready<=1;receipts++;end end
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
 reg [7:0] packet[0:255];reg [7:0] val;
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
  $display("PASS BATCH260 GUARD=%0d SHARED=%0d",GUARD,SHARED);$finish;
 end endtask
 task batch_packet(input integer seq,input [31:0] tok,input integer ranges,seed,bad);
 integer n,len;reg [15:0] c;begin
  for(integer i=0;i<256;i++)packet[i]=0;
  packet[0]=14;packet[1]=bank;packet[2]=seq;packet[3]=seq>>8;
  for(integer i=0;i<4;i++)begin packet[4+i]=serial>>(8*i);packet[16+i]=tok>>(8*i);end
  packet[8]=gen;packet[9]=gen>>8;packet[20]=ranges;n=21;
  for(integer r=0;r<ranges;r++)begin
   len=GUARD==32?2:(r%3+1)*2;
   packet[n]=r*8;packet[n+1]=(r*8)>>8;packet[n+2]=len;n+=3;
   for(integer j=0;j<len;j++)packet[n+j]=seed+r*32+j;
   n+=len;
  end
  case(bad)
   3:packet[20]=0;4:packet[20]=48;
   6:packet[21]=1;7:packet[23]=3;8:packet[23]=0;9:packet[23]=66;
   10:begin packet[21]=254;packet[22]=15;packet[23]=4;end
   11:begin packet[n]=42;n++;end
   26:packet[1]=!bank;27:packet[2]=seq+1;28:packet[8]=gen+1;
   29:packet[20]=1;30:packet[20]=ranges+1;
   default:;
  endcase
  packet[12]=n-16;packet[13]=(n-16)>>8;
  @(negedge hc);ss=0;c=crc16(16'hffff,8'he1);spi_byte(8'he1);
  for(integer i=0;i<n;i++)begin spi_byte(packet[i]);c=crc16(c,packet[i]);end
  spi_byte(c[15:8]);spi_byte(c[7:0]^(bad==35));#190;ss=1;repeat(8)@(negedge hc);
 end endtask
 task range_dma(input integer r,seed,input [31:0] tok,input integer consume_it);
 begin wait(dut.state==dut.DMA&&dut.chunk_token==tok);dma((GUARD==32?2:(r%3+1)*2),seed+r*32,tok,consume_it);end endtask
 task completed;begin
  if(fault)$fatal(1,"unexpected fault");
  $display("PASS BATCH260 GUARD=%0d SHARED=%0d ticks=%0d receipts=%0d retired=%0d next=%0d bytes=%0d",GUARD,SHARED,ticks,receipts,dut.queue.retired,nt,dma_bytes);$finish;
 end endtask
 task restart_batch;reg [31:0] next;begin
  next=nt;stopped();hold_receipt=0;end_tiles();batch_packet(0,next,2,100,0);
  range_dma(0,100,next,1);range_dma(1,100,next+1,1);wait(dut.queue.retired==1);final_ack(next+1);
  if(nt!=next+2)$fatal(1,"STOP burned wrong tokens");completed();
 end endtask
 initial begin
  fd=$fopen("events.csv","w");repeat(8)@(negedge hc);reset=0;repeat(12)@(negedge hc);admit();if(GUARD!=36)end_tiles();
  if(GUARD==2)begin batch_packet(0,0,3,80,0);rejected();end
  if(GUARD==3||GUARD==4||(GUARD>=6&&GUARD<=10)||(GUARD>=26&&GUARD<=29)||GUARD==35)begin batch_packet(0,1,3,80,GUARD);rejected();end
  if(GUARD==12)begin batch_packet(0,32'hfffffffe,2,80,0);wait(fault);if(nt!=32'hfffffffe)$fatal(1,"overflow allocated");rejected();end
  if(GUARD==33)begin batch_packet(0,32'hfffffffe,1,80,0);range_dma(0,80,32'hfffffffe,1);wait(dut.queue.retired==1);batch_packet(1,32'hffffffff,1,80,0);rejected();end
  if(GUARD==25)begin
   for(integer i=0;i<4;i++)batch_packet(i,i*3+1,3,80,0);
   if(dut.queue.accepted!=4||dut.queue.retired!=0)$fatal(1,"credit not held");batch_packet(4,13,3,80,0);rejected();
  end
  if(GUARD==17)begin fork batch_packet(0,1,3,80,0);begin wait(dut.state==dut.PUT);restart_batch();end join end
  if(GUARD==32)begin
   batch_packet(0,1,47,80,0);
   for(integer r=0;r<47;r++)begin range_dma(r,80,r+1,1);if(r<46&&dut.queue.retired!=0)$fatal(1,"early max packet retire");end
   wait(dut.queue.retired==1);final_ack(47);if(receipts!=47||nt!=48||dma_bytes!=94)$fatal(1,"max packet");completed();
  end
  if(GUARD==11||GUARD==30)begin batch_packet(0,1,3,80,GUARD);range_dma(0,80,1,1);range_dma(1,80,2,1);wait(fault);if(dut.queue.retired!=0)$fatal(1,"malformed tail retired");rejected();end
  if(GUARD==21||GUARD==1)hold_receipt=1;
  batch_packet(0,1,3,80,0);
  if(GUARD==36)begin
   wait(staged);tile(0,90);
   fork end_tiles();begin
    for(integer r=0;r<3;r++)begin range_dma(r,80,r+1,1);if(dut.owner!=dut.MAP)$fatal(1,"tile stole batch owner");end
    wait(dut.owner==dut.TILE&&staged);dma(16,90,4,1);wait(dut.owner==dut.NONE);
   end join
   final_ack(3);
   if(receipts!=3||nt!=5||dma_bytes!=28)$fatal(1,"tile competition totals");completed();
  end
  if(GUARD==15)begin wait(staged);wr(24'h006010,0);rejected();end
  if(GUARD==18||GUARD==19)begin
   fork range_dma(0,80,1,1);begin wait(dut.remaining==2&&dut.state==(GUARD==18?dut.DCAP:dut.PUT));restart_batch();end join
  end
  range_dma(0,80,1,1);
  if(GUARD==1||GUARD==21)begin
   wait(dut.state==dut.WAIT_RECEIPT);repeat(200)@(negedge hc);
   if(dut.queue.retired!=0||nt!=2||ordinary)$fatal(1,"receipt bypass");
   if(GUARD==21)restart_batch();hold_receipt=0;
  end
  wait(dut.state==dut.DMA&&dut.chunk_token==2);
  if(dut.queue.retired!=0||ordinary)$fatal(1,"early first range retire");
  if(GUARD==13||GUARD==16)begin range_dma(1,80,2,0);write_token(1);wr(24'h006050,8'ha5);rejected();end
  if(GUARD==14)begin dma(2,112,2,0);write_token(2);wr(24'h006050,8'ha5);rejected();end
  if(GUARD==20)begin dma(2,112,2,0);restart_batch();end
  if(GUARD==23)begin batch_packet(1,4,3,160,0);if(dut.queue.accepted!=2)$fatal(1,"queued future token");restart_batch();end
  if(GUARD==31)begin sealed=1;repeat(10)@(negedge hc);write_token(1);wr(24'h006058,8'h5a);rejected();end
  range_dma(1,80,2,1);
  if(GUARD==22)begin fork range_dma(2,80,3,1);begin wait(dut.state==dut.CONSUME&&dut.chunk_token==3);restart_batch();end join end
  range_dma(2,80,3,1);wait(dut.queue.retired==1);
  if(GUARD==24)begin final_ack(3);serial++;gen++;bank=!bank;admit();end_tiles();batch_packet(0,1,2,80,0);rejected();end
  if(GUARD==1)begin final_ack(3);completed();end
  // Fill all four credits with a batch/ordinary mix. The second batch must
  // retain its one head through three separate DMA/receipt lifetimes.
  send_packet(2,1,0,0);batch_packet(2,4,3,160,0);send_packet(2,3,0,0);batch_packet(4,7,3,40,0);
  if(dut.queue.accepted!=5||dut.queue.retired!=1||!ordinary)$fatal(1,"four credits");
  ordinary_ack(1,0);
  for(integer r=0;r<3;r++)begin range_dma(r,160,r+4,1);if(dut.queue.retired!=2)$fatal(1,"batch head released before last receipt");end
  wait(dut.queue.retired==3);ordinary_ack(3,0);
  for(integer r=0;r<3;r++)range_dma(r,40,r+7,1);
  wait(dut.queue.retired==5);final_ack(9);
  for(integer frame=2;frame<=3;frame++)begin
   serial=frame;gen=frame;bank=(frame==2);admit();end_tiles();batch_packet(0,(frame-2)*2+10,2,frame*40,0);
   range_dma(0,frame*40,(frame-2)*2+10,1);range_dma(1,frame*40,(frame-2)*2+11,1);wait(dut.state==dut.IDLE&&!dut.qr);final_ack((frame-2)*2+11);
  end
  if(receipts!=13||acks!=3||ordinary_count!=2||nt!=14||dma_bytes!=48||dut.queue.retired!=7)$fatal(1,"final totals");completed();
 end
 initial begin #30000000;$fatal(1,"watchdog state%0d owner%0d fault%0d",dut.state,dut.owner,fault);end
endmodule
