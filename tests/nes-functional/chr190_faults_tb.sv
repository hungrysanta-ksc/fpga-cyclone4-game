// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module chr190_faults_tb;
 reg nc=0,hc=0,reset=1,stop=0;
 always #23.28 nc=!nc;
 always #5.952 hc=!hc;
 reg valid=0;wire ready;reg [95:0] data=0;
 wire pr,av,aa;wire [15:0] ag;
 reg [31:0] seed=32'h10000;
 wire cr;wire [11:0] len;wire [31:0] token;
 reg [23:0] address=0;reg rn=1;
 wire [7:0] dout;wire oe,dir,busy,fault;
 nes_source_bulk190 dut(.nes_clk(nc),.host_clk(hc),.raw_reset(reset),.active(1'b1),.stop(stop),
  .record_valid(valid),.record_ready(ready),.record_data(data),
  .prepared_valid(1'b0),.prepared_ready(pr),.prepared_accept(1'b0),.prepared_generation(16'd0),
  .ack_valid(av),.ack_ready(1'b1),.ack_accept(aa),.ack_generation(ag),.token_seed(seed),
  .chunk_ready(cr),.chunk_length(len),.chunk_token(token),.consume(1'b0),.consume_token(32'd0),
  .address(address),.read_n(rn),.write_n(1'b1),.data_out(dout),.oe_n(oe),.dir(dir),.busy(busy),.fault(fault));
 task tick;begin @(posedge hc);#1;end endtask
 task fresh;begin
  @(negedge hc);reset=1;valid=0;rn=1;seed=seed+32'h100;
  repeat(6)@(posedge nc);@(negedge nc);reset=0;repeat(12)@(posedge nc);
 end endtask
 task send(input [95:0] word);begin
  @(negedge nc);while(!ready)@(negedge nc);
  data=word;valid=1;@(posedge nc);@(negedge nc);valid=0;
 end endtask
 function automatic [95:0] chr(input [12:0] tag,input [15:0] gen,input [1:0] kind,input [3:0] lane,input [7:0] value);
  chr={3'd6,gen,tag,50'd0,kind,lane,value};
 endfunction
 task readbyte(input integer at,input [7:0] expected);begin
  @(negedge hc);address=24'h400800+at;rn=0;repeat(4)tick();
  if(oe||dout!==expected)$fatal(1,"byte %d got %x wanted %x",at,dout,expected);
  rn=1;
 end endtask
 integer mode,j;
 reg [95:0] bad;
 initial begin
  for(mode=0;mode<8;mode=mode+1)begin
   fresh();
   if(mode==0)send(chr(13'd3,16'd12,2'd1,4'd1,8'h11));
   else if(mode==7)send({3'd7,16'd12,13'd0,16'h1811,48'd0});
   else begin
    send(chr(13'd3,16'd12,2'd1,4'd0,8'h10));
    bad=chr(13'd3,16'd12,2'd1,4'd1,8'h11);
    case(mode)
     1:bad[11:8]=2;
     2:bad[76:64]=4;
     3:bad[92:77]=13;
     4:bad[13:12]=2;
     5:bad[14]=1;
     6:bad={3'd7,16'd12,13'd4,64'd0};
    endcase
    send(bad);
   end
   repeat(100)tick();
   if(!fault||cr)$fatal(1,"malformed tile escaped mode=%d",mode);
  end
  fresh();
  for(j=0;j<5;j=j+1)send(chr(13'd3,16'd12,2'd1,4'(j),8'(j)));
  send({3'd7,16'd12,13'd2,64'd5});
  wait(cr);if(fault||len!=12)$fatal(1,"partial tile ABORT");
  readbyte(0,8'he0);readbyte(1,8'h02);readbyte(2,0);readbyte(3,12);
  for(j=4;j<11;j=j+1)readbyte(j,0);readbyte(11,5);
  fresh();
  for(j=0;j<8;j=j+1)send(chr(13'd3,16'd12,2'd1,4'(j),8'(j)));
  repeat(50)tick();@(negedge hc);stop=1;seed=seed+1;
  #1;if(cr||!oe)$fatal(1,"STOP exposed old fragment");
  repeat(6)@(posedge nc);@(negedge nc);stop=0;repeat(12)@(posedge nc);
  for(j=0;j<16;j=j+1)send(chr(13'd3,16'd12,2'd3,4'(j),8'(128+j)));
  send({3'd7,16'd12,13'd1,64'd0});
  wait(cr);if(fault||len!=34||token!=seed)$fatal(1,"restart length/token");
  readbyte(0,8'hc0);readbyte(1,3);readbyte(2,0);readbyte(3,12);readbyte(4,3);readbyte(5,0);
  for(j=0;j<16;j=j+1)readbyte(j+6,8'(128+j));
  readbyte(22,8'he0);readbyte(23,1);
  $display("PASS CHR190FAULT cases=10");$finish;
 end
 initial begin #10000000;$fatal(1,"fault test timeout");end
endmodule
