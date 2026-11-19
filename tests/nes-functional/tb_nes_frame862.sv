`timescale 1ns/1ps
module tb_nes_frame862;
 reg clk=0,reset=1,active=1,rd=1,wr=1,pawr=1,ss=1,sck=0,mosi=0;
 reg [23:0] addr=0;
 reg [7:0] data=0,pa=0,b;
 wire selected,miso,drive;
 always #6 clk=~clk;
 nes_screen_status151 dut(.clk(clk),.reset(reset),.active(active),.pawr_n(pawr),.port_id(pa),
   .address(addr),.read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(data),.bus_drive(1'b0),
   .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.receive_write(drive),.selected(selected),.miso(miso));
 reg [7:0] snapshot[0:43];reg [15:0] expected[0:15];integer fd;
 task octet(input [7:0] v,output [7:0] r);
  for(integer i=7;i>=0;i=i-1)begin mosi=v[i];#190;sck=1;#95;r[i]=miso;#95;sck=0;end
 endtask
 task query(input [7:0] op,input integer n);
  ss=0;#200;octet(op,b);
  for(integer j=1;j<n;j++)begin octet(0,b);snapshot[j]=b;end
  if(op==8'h78 && !selected)$fatal(1,"missing 78 selection");
  ss=1;#220;
 endtask
 task head;
  addr=24'h400000;data=3;#120;rd=0;#180;rd=1;#120;
 endtask
 task write_byte(input [23:0] a,input [7:0] v);
  addr=a;data=v;#93;wr=0;#123;wr=1;#110;
 endtask
 task dma(input [15:0] offset,input [7:0] portno);
  addr={8'h7f,offset};pa=portno;#121;rd=0;pawr=0;#189;rd=1;pawr=1;#200;
 endtask
 task stamp(input integer n);
  expected[n]=dut.trace.now;
 endtask
 task check_word(input integer k);
  reg [15:0] t;
  t={snapshot[8+2*k],snapshot[7+2*k]};
  if(expected[k]-t>1 || (^t===1'bx))$fatal(1,"stamp %d got %x expected %x",k,t,expected[k]);
 endtask
 initial begin
  #100;reset=0;#160;head();stamp(0);
  dma(0,8'h18);stamp(4);#4000;dma(15,8'h19);stamp(5);
  dma(16'hc001,8'h18);stamp(6);stamp(7);
  dma(16'hd201,8'h19);stamp(8);stamp(9);
  #16700000;dma(16'he961,8'h18);stamp(10);stamp(11);
  dma(16'he000,8'h22);stamp(12);stamp(13);dma(16'he200,4);stamp(14);stamp(15);
  pa=0;addr='h2100;#90;pawr=0;#155;pawr=1;#105;stamp(1);
  write_byte('h6018,'hfe);write_byte('h6019,'h23);write_byte('h601c,'ha5);stamp(2);
  query('he0,20);stamp(3);query('h78,44);
  if({snapshot[1],snapshot[2],snapshot[3],snapshot[4],snapshot[5],snapshot[6]}!==48'h86210f7ffe23)$fatal(1,"header");
  if(snapshot[43]!==8'h13 || {snapshot[40],snapshot[39]}!={snapshot[26],snapshot[25]} ||
     {snapshot[42],snapshot[41]}!={snapshot[28],snapshot[27]})$fatal(1,"map to raw DMA gap");
  for(integer k=0;k<16;k++)check_word(k);
  fd=$fopen("receipt.hex","w");$fwrite(fd,"00");
  for(integer j=1;j<44;j++)$fwrite(fd,"%02x",snapshot[j]);
  $fclose(fd);
  head();query('h78,39);if(snapshot[3]!=1 || snapshot[4]!=0)$fatal(1,"stale row");
  active=0;#120;head();query('h78,39);if(snapshot[3]!=0 || snapshot[4]!=0)$fatal(1,"STOP");
  $display("PASS862 wire, six DMA classes, generations, ACK and STOP");$finish;
 end
endmodule
