// SPDX-License-Identifier: MIT
module ring373_tb;
 parameter CASE=0;
 reg src_clk=0,host_clk=0;always #22.727272727 src_clk=~src_clk;always #5.952380952 host_clk=~host_clk;
 reg reset=1,abort_source=0,record_valid=0,byte_valid=0,record_last319=0,record_flush=0;
 reg [7:0] record_length=124,byte_data=0;wire record_ready,byte_ready,crc_pending,source_fault,host_fault,source_empty;
 wire [15:0] crc_previous;wire [7:0] crc_byte;wire [15:0] crc_result=c16(crc_previous,crc_byte);
 reg ss=1,sck=0,mosi=0;wire selected,miso,ack_valid,ack_accept;wire [15:0] ack_generation;
 wire [113:0] link270;wire [199:0] status270;wire crc_take270;
 nes_spi270 front(.clk(host_clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.source_status(status270),.output_status(200'd0),.plan_status(200'd0),
 .request_crc_enable(crc_take270),.queue_admit319(1'b0),.plan_admit319(1'b0),.link(link270));
 nes_transport257 dut(.record_last319(record_last319),.link270(link270),.status270(status270),.crc_take270(crc_take270),.crc_result(crc_result),.crc_pending(crc_pending),
 .crc_previous(crc_previous),.crc_byte(crc_byte),.frame_generation(16'd7),.src_clk(src_clk),.host_clk(host_clk),.reset(reset),.abort_source(abort_source),
 .record_valid(record_valid),.record_ready(record_ready),.record_length(record_length),.record_flush(record_flush),.byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso),.ack_valid(ack_valid),.ack_ready(1'b0),.ack_accept(ack_accept),.ack_generation(ack_generation),
 .source_fault(source_fault),.host_fault(host_fault),.source_empty(source_empty));
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);reg [15:0] c;begin c=c0^{b,8'd0};for(integer j=0;j<8;j++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end endfunction
 function automatic [7:0] c8(input [7:0] c0,input [7:0] b);reg [7:0] c;begin c=c0^b;for(integer j=0;j<8;j++)c=c[7]?(c<<1)^8'h07:c<<1;c8=c;end endfunction
 reg [7:0] tx[0:300],rx[0:300];integer ack_count=0;
 always @(posedge src_clk)if(ack_valid)ack_count++;
 task record124(input integer start,input bit final_record);
 begin
  @(negedge src_clk);record_valid=1;record_flush=final_record;
  while(!record_ready)@(negedge src_clk);
  @(negedge src_clk);record_valid=0;
  for(integer j=0;j<124;j++)begin
   byte_valid=1;byte_data=(start+j)&255;record_last319=j==123;
   while(!byte_ready)@(negedge src_clk);
   @(negedge src_clk);byte_valid=0;record_last319=0;
   @(negedge src_clk);
  end
 end endtask
 task prefix(input [7:0] command,input integer token,input integer generation,input integer flags);
 reg [7:0] c;begin
  tx[0]=command;tx[1]=token>>8;tx[2]=token;tx[3]=generation;tx[4]=generation>>8;tx[5]=flags;
  c=0;for(integer j=0;j<6;j++)c=c8(c,tx[j]);tx[6]=c;tx[7]=8'ha5;
  for(integer j=8;j<301;j++)tx[j]=0;
 end endtask
 task shift(input integer lo,input integer hi);
 begin
  for(integer j=lo;j<hi;j++)begin
   rx[j]=0;
   for(integer b=7;b>=0;b--)begin mosi=tx[j][b];#190.476190476;sck=1;rx[j][b]=selected?miso:0;#190.476190476;sck=0;end
  end
 end endtask
 task read_packet(input integer token,input integer flags,input integer packet);
 reg [7:0] c;reg [15:0] crc;
 begin
  prefix(8'hd4,token,7,flags);ss=0;shift(0,13);
  c=0;for(integer j=8;j<12;j++)c=c8(c,rx[j]);
  if(c!=rx[12]||rx[8]!=8'hab||rx[9]!=248||{rx[10],rx[11]}!=packet)$fatal(1,"D4 header packet%0d %h %h %h %h %h",packet,rx[8],rx[9],rx[10],rx[11],rx[12]);
  shift(13,263);ss=1;#1000;
  crc=16'hffff;for(integer j=0;j<248;j++)begin
   if(rx[13+j]!==((packet*248+j)&255))$fatal(1,"payload packet%0d byte%0d",packet,j);
   crc=c16(crc,rx[13+j]);
  end
  if(crc!={rx[261],rx[262]})$fatal(1,"payload CRC");
 end endtask
 initial begin
  repeat(5)@(negedge src_clk);reset=0;repeat(12)@(negedge src_clk);
  for(integer p=0;p<4;p++)begin record124(p*248,0);record124(p*248+124,p==3);end
  wait(dut.full);repeat(30)@(negedge host_clk);
  if(dut.wbin!=4||dut.rbin!=0||source_fault||host_fault)$fatal(1,"four-slot ring full");
  read_packet(0,0,0);
  if(CASE==0)begin
   for(integer p=1;p<4;p++)read_packet(p-1,1,p);
   prefix(8'hd5,3,7,3);ss=0;shift(0,8);ss=1;#3000;
   if(!ack_valid||!ack_accept||ack_generation!=7||source_fault||host_fault||dut.rbin!=4)$fatal(1,"final input ACK");
  end else begin
   case(CASE)
    1:prefix(8'hd4,9,7,1);
    2:prefix(8'hd4,0,8,1);
    3:begin prefix(8'hd4,0,7,1);tx[6]=tx[6]^1;end
    4:prefix(8'hd4,0,7,1);
    5:prefix(8'hd5,0,7,3);
    6:begin abort_source=1;#2000;end
    7:begin force dut.token=16'hffff;prefix(8'hd4,65535,7,1);end
    8:prefix(8'hd4,0,7,0);
   endcase
   if(CASE!=6)begin ss=0;shift(0,CASE==4?7:8);ss=1;#2000;end
   if(!host_fault||ack_valid||dut.rbin!=0)$fatal(1,"guard accepted bad retire case%0d",CASE);
   begin reg [2:0] saved_w;reg [7:0] saved_byte;saved_w=dut.wbin;saved_byte=dut.memory[0];
    record_valid=1;byte_valid=1;byte_data=99;repeat(20)@(negedge src_clk);
    if(dut.wbin!=saved_w||dut.memory[0]!==saved_byte||byte_ready||record_ready)$fatal(1,"RAM write after fault");
   end
  end
  $display("PASS RING373 case=%0d",CASE);$finish;
 end
 initial begin #20000000;$fatal(1,"ring timeout");end
endmodule
