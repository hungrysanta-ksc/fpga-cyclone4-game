// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module source_bulk189_tb;
 parameter integer FAULT=0;
 parameter integer LARGE=0;
 parameter real PHASE=0;
 reg clk=0,host_clk=0,reset=1;
 always #23.28 clk=!clk;
 initial begin #PHASE;forever #5.952 host_clk=!host_clk;end
 wire valid,ready,av,aa,ack_ready;wire [95:0] data;wire [15:0] ag;
 `include "wire181_source.svh"
 reg pv=0,pa=1;reg [15:0] pg=0;wire pr;
 reg consume=0;reg [31:0] ct=0;wire cr;wire [11:0] len;wire [31:0] token;
 reg [23:0] address=0;reg read_n=1,write_n=1;
 wire [7:0] dout;wire oe,dir,busy,fault;
 nes_source_bulk189 bridge(.nes_clk(clk),.host_clk(host_clk),.raw_reset(reset),.active(1'b1),.stop(1'b0),
  .record_valid(valid),.record_ready(ready),.record_data(data),
  .prepared_valid(pv),.prepared_ready(pr),.prepared_accept(pa),.prepared_generation(pg),
  .ack_valid(av),.ack_ready(ack_ready),.ack_accept(aa),.ack_generation(ag),.token_seed(32'h10000),
  .chunk_ready(cr),.chunk_length(len),.chunk_token(token),.consume(consume),.consume_token(ct),
  .address(address),.read_n(read_n),.write_n(write_n),.data_out(dout),.oe_n(oe),.dir(dir),.busy(busy),.fault(fault));
 integer host_fd,chunk_fd,total_bytes=0,chunks=0,stalls=0,quiet=0,full_stalls=0;
 integer i,size,offset,kind,index,width,ending,commits=0,aborts=0;
 reg [7:0] bytes[0:2047];reg [31:0] saved_token;
 always @(posedge clk)if(!reset&&valid&&!ready)stalls<=stalls+1;
 always @(posedge host_clk)if(!reset&&bridge.aperture.sealed==3&&bridge.word_valid&&!bridge.word_ready)
  full_stalls<=full_stalls+1;
 task ht;begin @(posedge host_clk);#1;end endtask
 task prepared_ack(input integer gen);begin
  while(!pr)ht();@(negedge host_clk);pg=gen;pv=1;ht();@(negedge host_clk);pv=0;
 end endtask
 initial begin
  record_fd=$fopen("records.hex","w");host_fd=$fopen("read.hex","w");chunk_fd=$fopen("chunks.tsv","w");
  #200;reset=0;repeat(20)@(posedge clk);@(negedge clk);owned=1;
  // Let both slots fill if this scene is large enough: producer must stall safely.
  repeat(LARGE?100000:16000)ht();
  while(quiet<100)begin
   if(fault)$fatal(1,"bridge fault");
   if(cr)begin
    quiet=0;size=len;saved_token=token;ending=0;
    if(size==0||size>2048)$fatal(1,"chunk length");
    // A bad consume cannot change the head or destroy its immutable payload.
    @(negedge host_clk);consume=1;ct=saved_token+32'h100000;ht();
    if(!cr||token!=saved_token||len!=size)$fatal(1,"bad consume changed head");
    @(negedge host_clk);consume=0;ht();
    for(i=0;i<size;i=i+1)begin
     @(negedge host_clk);address=24'h400800+i;read_n=0;
     repeat(4)ht();if(oe||!dir)$fatal(1,"missing bus response");
     bytes[i]=dout;$fwrite(host_fd,"%02x\n",dout);total_bytes=total_bytes+1;
    end
    read_n=1;
    offset=0;
    while(offset<size)begin
     kind=bytes[offset]>>5;index=((bytes[offset]&31)<<8)|bytes[offset+1];
     case(kind)0,6:width=2;1,5:width=1;2,4:width=7;3:width=4;default:width=8;endcase
     if(offset+4+width>size)$fatal(1,"split record");
     if({bytes[offset+2],bytes[offset+3]}!=16'd12)$fatal(1,"mixed generation");
     if(kind==7&&index==1)ending=1;
     if(kind==7&&index==3)commits=commits+1;
     if(kind==7&&index==2)aborts=aborts+1;
     offset=offset+4+width;
    end
    $fwrite(chunk_fd,"%0d %0d %0d\n",saved_token,size,ending);
    @(negedge host_clk);ct=saved_token;consume=1;ht();@(negedge host_clk);consume=0;chunks=chunks+1;
    if(ending)begin
     if(!owned||released)$fatal(1,"source lease released before PREPARED");
     prepared_ack(13);repeat(20)@(posedge clk);
     if(!owned||export_finished)$fatal(1,"wrong generation released source");
     prepared_ack(12);
    end
   end else begin ht();if(export_finished&&!busy)quiet=quiet+1;else quiet=0;end
  end
  if(FAULT)begin if(aborts!=1||commits!=0)$fatal(1,"fault not ABORT");end
  else if(commits!=1||aborts!=0||ee!=0)$fatal(1,"missing COMMIT");
  if(LARGE&&full_stalls==0)$fatal(1,"two-slot pressure not exercised");
  $fclose(record_fd);$fclose(host_fd);$fclose(chunk_fd);
  $display("PASS SOURCE189 bytes=%0d chunks=%0d records=%0d stalls=%0d commit=%0d abort=%0d",total_bytes,chunks,exported,stalls,commits,aborts);
  $display("FULL_SLOT_WAIT hostcycles=%0d",full_stalls);
  $finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
