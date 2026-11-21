`timescale 1ns/1ps
module tb_nes_frame900;
 reg clk=0,reset=1,active=0,rd=1,wr=1,pawr=1,ss=1,sck=0,mosi=0;
 reg [23:0] a=0;
 reg [7:0] drive=0,pa=0;
 wire [7:0] out,data,op,d;
 wire [15:0] gen;
 wire header,section_r,retired,oe,dir,sel,miso,fault;
 always #6 clk=~clk;
 assign data=!rd && !oe && dir ? out : drive;
 nes_sink_bridge165 sink(.clk(clk),.raw_reset(reset),.active(active),.stop(1'b0),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.address(a),.read_n(rd),.write_n(wr),
  .romsel_n(1'b1),.data_in(data),.data_out(out),.oe_n(oe),.dir(dir),.fault(fault),
  .tr_head(header),.tr_section(section_r),.tr_retired(retired),.tr_gen(gen),.tr_op(op),.tr_data(d));
 nes_screen_status151 monitor(.clk(clk),.reset(reset),.active(active),.pawr_n(pawr),.port_id(pa),
  .address(a),.read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(data),.bus_drive(dir&&!oe),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(sel),.miso(miso),
  .tr_head(header),.tr_section(section_r),.tr_retired(retired),.tr_gen(gen),.tr_op(op),.tr_data(d));
 reg [7:0] snapshot[0:25],pkt[0:15],b;
 reg [15:0] exp_t[0:9],crc;
 task octet(input [7:0] v,output [7:0] r);
  for(integer k=7;k>=0;k--)begin mosi=v[k];#190;sck=1;#95;r[k]=miso;#95;sck=0;end
 endtask
 task crc_byte(input [7:0] v);
  crc=crc^{v,8'd0};repeat(8)crc=(crc<<1)^(crc[15]?16'h1021:16'd0);
 endtask
 task query;
  ss=0;#200;octet('h78,b);exp_t[9]=monitor.trace.now;
  for(integer k=1;k<26;k++)octet(0,snapshot[k]);
  if(!sel)$fatal(1,"SPI selection");ss=1;#250;
 endtask
 task write_byte(input integer at,input [7:0] v);
  a=at;drive=v;#90;wr=0;#150;wr=1;#140;
 endtask
 task read_byte(input integer at);
  a=at;#145;rd=0;#240;rd=1;#145;
 endtask
 integer seq=0;
 task packet(input integer g,input integer opcode,input integer section_id,input bit bad);
  for(integer k=0;k<16;k++)pkt[k]=0;
  pkt[0]=opcode;pkt[1]=section_id;pkt[2]=seq;pkt[4]=1;pkt[8]=g;pkt[9]=g>>8;
  crc='hffff;ss=0;#200;crc_byte('he1);octet('he1,b);
  for(integer k=0;k<16;k++)begin crc_byte(pkt[k]);octet(pkt[k],b);end
  octet(crc[15:8],b);octet(crc[7:0],b);ss=1;#600;
  read_byte('h400000);if(opcode==3)exp_t[2]=monitor.trace.now;
  read_byte('h400001);
  if(section_id==2)exp_t[0]=monitor.trace.now;
  if(opcode==7)exp_t[1]=monitor.trace.now;
  #7200;
  if(opcode==3)begin
   a='h7fe200;pa=4;#150;pawr=0;rd=0;#200;rd=1;pawr=1;#160;
   exp_t[3]=monitor.trace.now;#7200;
   a='h2100;pa=0;#150;pawr=0;#180;pawr=1;#170;exp_t[4]=monitor.trace.now;
  end
  #7200;
  write_byte('h6010,opcode==3);write_byte('h6011,opcode);
  for(integer k=2;k<10;k++)write_byte('h6010+k,pkt[k]^(bad && k==8));
  write_byte('h601a,'h65);write_byte('h601b,'h9a);write_byte('h601c,'ha5);#300;
  if(section_id==2)exp_t[7]=monitor.trace.now;
  if(opcode==7)exp_t[8]=monitor.trace.now;
  if(opcode==3)exp_t[5]=monitor.trace.now;
  seq++;
 endtask
 initial begin
  #130;reset=0;active=1;#1000;
  packet(904,1,0,0);packet(904,3,0,0);exp_t[6]=exp_t[4];
  packet(905,1,0,0);packet(905,2,2,0);packet(905,7,1,0);packet(905,9,2,0);packet(905,3,0,0);
  query();
  if(fault || {snapshot[1],snapshot[2],snapshot[4],snapshot[3]}!==32'h90ff0389 || snapshot[25]!==0)
   $fatal(1,"header %x %x %x %x fault=%d",snapshot[1],snapshot[2],snapshot[3],snapshot[4],fault);
  for(integer k=0;k<10;k++)begin
   if((exp_t[k]-{snapshot[6+2*k],snapshot[5+2*k]})>1 ||
      ^{snapshot[6+2*k],snapshot[5+2*k]}===1'bx)$fatal(1,"stamp %d",k);
  end
  packet(906,1,0,0);packet(906,7,0,1);query();
  if(!fault || snapshot[2][7] || snapshot[2][5])$fatal(1,"bad identity was retired");
  active=0;#400;query();if(snapshot[2]!==0)$fatal(1,"STOP left valid receipt");
  $display("PASS900 checked queue, both header bytes, last DMA, reveal, previous generation, bad identity, STOP");$finish;
 end
endmodule
