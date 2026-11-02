// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module plan_credit557_tb;
 reg hc=0,nc=0,reset=1,ss=1,sck=0,mosi=0,done=0;
 integer phase;
 always #5952 hc=~hc;
 initial begin if(!$value$plusargs("PHASE=%d",phase))phase=0;
  #(phase);forever #23281 nc=~nc;end
 wire idle,wr,pw,seal,pv,ev,ret,rd,spi_fault,batch_fault,miso;
 wire [7:0] pd,mask;wire [9:0] pl,slot;wire [4:0] pn;
 wire [15:0] pc,g;wire [1:0] kind;wire [12:0] tag;
 nes_plan_spi200 ep(.clk(hc),.reset(reset),.enable(1'b1),.stop(1'b0),.source_fault(batch_fault),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(miso),.fault(spi_fault),.plan_idle(idle),.plan_ready(wr),
  .plan_write(pw),.plan_data(pd),.plan_seal(seal),.plan_length(pl),.plan_plans(pn),.plan_crc(pc),
  .retire_done(rd),.retire(ret),.end_generation(16'd954),.end_sealed(1'b0),
  .chunk_ready(1'b0),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),.chunk_generation(16'd0),.chunk_token(32'd0));
 nes_plan_batch206 transport(.host_clk(hc),.nes_clk(nc),.reset(reset),.stop(1'b0),.active(1'b1),.source_fault(spi_fault),
  .write_valid(pw),.write_ready(wr),.write_data(pd),.seal(seal),.seal_length(pl),.seal_plans(pn),.seal_crc(pc),
  .retire(ret),.retire_done(rd),.retire_permitted(1'b0),.host_idle(idle),.fault(batch_fault),
  .lease_valid(1'b1),.lease_generation(16'd954),.plan_valid(pv),.plan_ready(1'b1),.tile_done(done),
  .plan_generation(g),.plan_kind(kind),.plan_slot(slot),.plan_tag(tag),.plan_mask(mask),.end_valid(ev),.end_ready(1'b1));
 reg [7:0] raw[0:195],rx[0:19];reg [32:0] expected[0:22];integer accepted_plans=0,ends=0;
 integer nes_edges=0,entry_edge=-1,record_bytes;
 always @(posedge nc)begin
  nes_edges=nes_edges+1;
  if(reset)begin accepted_plans=0;ends=0;entry_edge=-1;end
  else begin
   if(transport.state==1 && transport.at==0)entry_edge=nes_edges;
   if(transport.state==3)begin
    record_bytes=transport.length;
    if(nes_edges-entry_edge!=2*record_bytes)$fatal(1,"READ/CAPTURE/CHECK latency");
    if(transport.word_ready)$display("CHECK phase=%0d count=%0d t=%0t",phase,accepted_plans,$time);
   end
   if(pv)begin
    if(accepted_plans>=23||expected[accepted_plans]!=={kind,slot,tag,mask}||g!=954)$fatal(1,"decoded plan %0d",accepted_plans);
    accepted_plans=accepted_plans+1;
   end
   if(ev)begin if(accepted_plans!=23)$fatal(1,"early END");ends=ends+1;end
  end
 end
 task automatic byte_io(input reg [7:0] value,output reg [7:0] reply);
  for(integer j=7;j>=0;j--)begin mosi=value[j];#190476;sck=1;reply[j]=miso;#190476;sck=0;end
 endtask
 task automatic transmit(input integer a,n);reg [7:0] x;
  ss=0;#80000;for(integer i=0;i<n;i++)byte_io(raw[a+i],x);#80000;ss=1;#200000;
 endtask
 function automatic [7:0] crc8(input [7:0] old,b);reg [7:0] c;
  c=old^b;for(integer j=0;j<8;j++)c=c[7]?(c<<1)^8'h07:c<<1;return c;
 endfunction
 task automatic status(input bit writable,input integer count);reg [7:0] c;
  ss=0;#80000;for(integer i=0;i<20;i++)byte_io(i==0?8'he8:8'd0,rx[i]);#80000;ss=1;#200000;
  c=0;for(integer i=1;i<=18;i++)c=crc8(c,rx[i]);
  if({rx[1],rx[2]}!==16'hd704||rx[3]!=={7'b0,writable}||{rx[4],rx[5]}!==count[15:0]||c!==rx[19])
   $fatal(1,"snapshot flags=%h count=%h crc=%h expected=%d/%d",rx[3],rx[5],rx[19],writable,count);
 endtask
 task automatic release_tile;
  wait(transport.state==5);@(negedge nc);done=1;@(negedge nc);done=0;
 endtask
 task automatic restart;
  reset=1;repeat(8)@(negedge nc);reset=0;repeat(20)@(negedge nc);status(1,0);
 endtask
 task automatic fill_two;
  transmit(0,32);wait(transport.state==5);status(1,1);transmit(32,121);status(0,2);
 endtask
 time origin,when_start,when_end,at_done;
 integer fd,df,op,count,offset,writable,batch,checked,early_wire;
 reg [7:0] octet,sum;
 task automatic timed;
  restart; origin=$time; batch=0; checked=0;
  if(!$value$plusargs("EARLY=%d",early_wire))early_wire=0;
  fork
   begin
    df=$fopen("done.dat","r");
    for(integer i=0;i<23;i++)begin
     if($fscanf(df,"%d",at_done)!=1)$fatal(1,"missing tile finish");
     wait(transport.state==5);
     if($time>origin+at_done+200000)$fatal(1,"tile unavailable on supplied finish %0d",i);
     if(origin+at_done>$time)#(origin+at_done-$time);
     release_tile;
    end
   end
   begin
    fd=$fopen("spi.dat","r");
    while($fscanf(fd,"%d %d %d %d %d %d",when_start,when_end,op,offset,count,writable)==6)begin
     if(origin+when_start<$time)$fatal(1,"overlapping SPI transactions");
     #(origin+when_start-$time);ss=0;
     for(integer j=0;j<count;j++)begin
      byte_io(op==233?raw[offset+j]:(j==0?8'he8:8'd0),octet);
      if(op==232)rx[j]=octet;
     end
     if(!early_wire && origin+when_end>$time)#(origin+when_end-$time);
     ss=1;
     if(op==232)begin
      sum=0;for(integer j=1;j<=18;j++)sum=crc8(sum,rx[j]);
      if(rx[3]!==writable[7:0]||{rx[4],rx[5]}!==batch[15:0]||rx[19]!==sum)
       $fatal(1,"E8 sample %0d actual=%h expected=%d",checked,rx[3],writable);
      checked++;
     end else batch++;
    end
   end
  join
  wait(ends==1);if(batch!=3||spi_fault||batch_fault)$fatal(1,"timed path");
  $display("PASS TIMED557 phase=%0d early=%0d E8=%0d plans=%0d",phase,early_wire,checked,accepted_plans);
 endtask
 initial begin
  $readmemh("requests.hex",raw);$readmemh("plans.hex",expected);
  if($test$plusargs("TIMED"))begin timed;$finish;end
  restart;fill_two;
  repeat(3)release_tile;
  wait(idle);$display("WRITABLE phase=%0d t=%0t",phase,$time);
  wait(transport.state==5);if(accepted_plans!=4)$fatal(1,"wrong tile owner");
  status(1,2);transmit(153,43);status(0,3);
  if(ends||spi_fault||batch_fault||accepted_plans!=4)$fatal(1,"early visibility");
  repeat(20)release_tile;wait(ends==1);
  if(spi_fault||batch_fault)$fatal(1,"consumer fault");
  restart;fill_two;restart;if(ends||accepted_plans||spi_fault||batch_fault)$fatal(1,"STOP left owned work");
  fill_two;transmit(153,43);if(!spi_fault)$fatal(1,"uncredited E9 accepted");
  $display("PASS BANK557 phase=%0d",phase);$finish;
 end
 initial #(64'd200000000000) $fatal(1,"timeout");
endmodule
