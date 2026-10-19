`timescale 1ns/1ps
// Actual packet/tile/staging/control RTL. The ordinary-command executor is
// an explicit bus/service model, not a65816 CPU. Its delays are assumptions.
module output260_tb;
 parameter SERIAL=1,GEN=1,FETCH_WAIT=4,QUEUE_SEED=0;
 reg hc=0,nc=0;always #5 hc=~hc;always #22.727 nc=~nc;
 reg reset=1,cancel=0,iv=0;wire ir;
 reg ss=1,sck=0,mosi=0;wire miso;
 reg transfer_start=0,transfer_done=0;integer transfer_length=0;
 reg [7:0] tx_bytes[0:258];reg [7:0] rx_byte;integer spi_fd;
 initial forever begin
  @(posedge transfer_start);transfer_done=0;$readmemh("spi-tx.hex",tx_bytes,0,transfer_length-1);
  spi_fd=$fopen("spi-rx.txt","w");ss=0;#100;
  for(integer byte259=0;byte259<transfer_length;byte259++)begin
   rx_byte=0;
   for(integer bit259=7;bit259>=0;bit259--)begin
    mosi=tx_bytes[byte259][bit259];#190.476;sck=1;#190.476;rx_byte={rx_byte[6:0],miso};sck=0;
   end
   $fwrite(spi_fd,"%02x",rx_byte);
  end
  #190.476;ss=1;#100;$fclose(spi_fd);transfer_done=1;
 end
 reg [23:0] address=0;reg rn=1,wn=1;reg [7:0] din=0;wire [7:0] dout;wire valid;
 reg tv=0,ev=0;wire tr,er;reg [7:0] td;reg [4:0] ti;reg [5:0] tl;reg [1:0] tk;reg [9:0] ts;
 wire rv,rdone,ack,retired,staged,receipt,fault,ordinary;wire [11:0] rf,rc;wire [31:0] nt;
 reg ready=1,sealed=0;integer delay=0;
 nes_output260 dut(.nes_clk(nc),.host_clk(hc),.reset(reset),.cancel(cancel),.identity_valid(iv),.identity_ready(ir),.serial(32'(SERIAL)),.generation(16'(GEN)),.bank(1'((SERIAL-1)%2)),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(miso),.address(address),.read_n(rn),.write_n(wn),.data_in(din),.data_out(dout),.bus_valid(valid),
 .tile_valid(tv),.tile_ready(tr),.tile_data(td),.tile_index(ti),.tile_length(tl),.tile_kind(tk),.tile_slot(ts),.tile_generation(16'(GEN)),
 .end_valid(ev),.end_ready(er),.end_generation(16'(GEN)),.range_valid(rv),.range_ready(ready),.range_first(rf),.range_count(rc),.range_dma_done(rdone),
 .sealed(sealed),.core_idle(1'b1),.display_ack(ack),.retired(retired),.staged(staged),.receipt_committed(receipt),.fault(fault),.ordinary_ready(ordinary),.next_token(nt));
 always @(posedge nc)begin
  if(rv&&ready)begin ready<=0;delay<=8;end
  if(delay>0)begin delay<=delay-1;if(delay==1)ready<=1;end
 end
 integer ticks=0,tile_wait=0,map_wait=0,normal_count=0,dma_bytes=0,dma_chunks=0;
 // Directed counter-wrap seed, before any SPI transaction/identity. No RAM
 // data or output is injected; the queue remains empty with equal counters.
 initial begin wait(!reset);@(negedge hc);dut.queue.accepted=QUEUE_SEED;dut.queue.retired=QUEUE_SEED;end
 always @(posedge hc)begin
  ticks++;
  if(!reset&&fault)$fatal(1,"OUTPUT259 state=%0d q=%0d t=%0d fail=%0d serial=%0d",dut.state,dut.qfault,dut.tfault,dut.failed,SERIAL);
  if(!reset&&dut.trequest&&dut.owner!=dut.TILE)tile_wait++;
  if(!reset&&dut.state==dut.OPEN&&dut.owner==dut.TILE)map_wait++;
 end
 reg [7:0] tile_bytes[0:32767],expected[0:8569],metadata[0:8569];
 reg [63:0] tile_desc[0:1151];integer tile_count,tile_size;reg initialized=0,finished=0;
 integer fd,n,j,k,z,at,slot,unit,chunk,off,logfd;reg [63:0] desc;
 initial begin
  fd=$fopen("sizes.txt","r");z=$fscanf(fd,"%d %d",tile_count,tile_size);$fclose(fd);
  if(tile_count>0)$readmemh("tiles.hex",tile_bytes,0,tile_size-1);
  if(tile_count>0)$readmemh("tile-desc.hex",tile_desc,0,tile_count-1);
  $readmemh("expected.hex",expected);$readmemh("prior.hex",metadata);
  logfd=$fopen("events.csv","w");repeat(10)@(negedge hc);reset=0;wait(ir);@(negedge nc);iv=1;@(negedge nc);iv=0;repeat(16)@(negedge hc);initialized=1;
  at=0;
  for(k=0;k<tile_count;k++)begin
   desc=tile_desc[k];tk=desc[49:48];unit=tk==1?32:16;slot=desc[47:32];n=desc[31:0];tl=unit;
   for(j=0;j<n;j++)begin
    repeat(FETCH_WAIT)@(negedge nc);wait(tr);@(negedge nc);tv=1;ti=j%unit;ts=slot+j/unit;td=tile_bytes[at+j];@(negedge nc);tv=0;
   end
   at+=n;
  end
  wait(er);@(negedge nc);ev=1;@(negedge nc);ev=0;
 end
 task rd(input [23:0] a,output reg [7:0] b);begin
  @(negedge hc);address=a;rn=0;#200;if(!valid)$fatal(1,"bus read %h state%0d",a,dut.state);b=dout;rn=1;#200;
 end endtask
 task wr(input [23:0] a,input [7:0] b);begin @(negedge hc);address=a;din=b;wn=0;#200;wn=1;#200;end endtask
 task token(input [31:0] tok);begin for(integer i=0;i<4;i++)wr(24'h00604c+i,tok>>(8*i));end endtask
 reg [7:0] packet[0:255],value;integer length,base,count,first;reg [31:0] tok;integer tile_read=0;reg h2_seen=0;
 task dma;
 integer bytes,base259;reg ismap;begin
  ismap=dut.owner==dut.MAP;bytes=dut.chunk_length;tok=dut.chunk_token;base259=dut.first*2;
  // Fixed500 SNES master-clock setup allocation, not measured CPU time.
  #23280;
  for(integer i=0;i<bytes;i++)begin
   rd(24'h400800+i,value);
   if(ismap)metadata[base259+i]=value;
   else begin if(value!==tile_bytes[tile_read])$fatal(1,"tile DMA mismatch");tile_read++;end
   dma_bytes++;
  end
  token(tok);wr(24'h006050,8'ha5);dma_chunks++;
  if(ismap)wait(receipt);else repeat(8)@(negedge hc);
 end endtask
 task normal;
 begin
  length=dut.qlen;for(integer i=0;i<length;i++)rd(24'h400000+i,packet[i]);
  $fwrite(logfd,"ordinary,%0d,%0d,%0d\n",ticks,packet[0],length);
  if(packet[0]==7)begin
   wait(staged);if(dut.owner!=dut.TILE||dut.chunk_token!={packet[19],packet[18],packet[17],packet[16]}||dut.chunk_length!={packet[15],packet[14]})$fatal(1,"tile command ownership");dma();
  end else if(packet[0]==2||packet[0]==4||packet[0]==5||packet[0]==8)begin
   base=packet[1]==3?4096:packet[1]==4?4608:packet[1]==5?5152:-1;
   first={packet[11],packet[10]};count=packet[0]==2?{packet[13],packet[12]}:{packet[15],packet[14]};
   if(base<0||base+first+count>8570)$fatal(1,"ordinary range");
   for(integer i=0;i<count;i++)begin
    metadata[base+first+i]=packet[16+(packet[0]==2?i:packet[0]==8?i%4:i%2)];
    #560; // Explicit ordinary copy/fill service assumption.
   end
  end else if(packet[0]==13)begin
   if(length!=48||packet[16]!=8'h48||packet[17]!=8'h32)$fatal(1,"H2 shape");h2_seen=1;
  end else if(packet[0]==3)begin
   if(!h2_seen||tile_read!=tile_size)$fatal(1,"missing H2/tile consume");
   for(integer i=0;i<8570;i++)if(metadata[i]!==expected[i])$fatal(1,"metadata byte%0d got%h expected%h",i,metadata[i],expected[i]);
   sealed=1;
  end else if(packet[0]!=1&&packet[0]!=10&&packet[0]!=11)$fatal(1,"unknown ordinary");
  wr(24'h006010,packet[0]==3?1:0);wr(24'h006011,packet[0]);
  for(integer i=2;i<10;i++)wr(24'h006010+i,packet[i]);
  wr(24'h00601a,8'h65);wr(24'h00601b,8'h9a);wr(24'h00601c,8'ha5);wait(dut.qdone);@(negedge hc);normal_count++;
  if(packet[0]==3)begin
   wait(dut.state==dut.IDLE&&dut.owner==dut.NONE);token(dut.last_map_token);wr(24'h006058,8'h5a);wait(retired);finished=1;
   $display("PASS OUTPUT259 ticks=%0d bytes=%0d chunks=%0d ordinary=%0d tilewait=%0d mapwait=%0d",ticks,dma_bytes,dma_chunks,normal_count,tile_wait,map_wait);
  end
 end endtask
 initial begin wait(initialized);while(!finished)begin
  if(ordinary)normal();else if(staged&&dut.owner==dut.MAP&&dut.state==dut.DMA)dma();else repeat(20)@(negedge hc);
 end end
 initial begin #200000000;$fatal(1,"watchdog");end
endmodule
