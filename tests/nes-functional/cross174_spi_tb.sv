// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_spi165_tb;
 parameter real PHASE=0;
 reg clk=0,reset=1,ss=1,sck=0,mosi=0,valid=0,ack_ready=1;
 wire ready,selected,miso,av,aa,fault;wire [15:0] ag;reg [95:0] data=0;
 nes_native_spi165 dut(clk,reset,ss,sck,mosi,selected,miso,valid,ready,data,av,ack_ready,aa,ag,fault);
 always #5.952 clk=~clk;
 reg [95:0] records[0:4095];integer count,n,acks=0,blocks=0,wirebytes=0,fd;
 reg [7:0] tx[0:258],rx[0:258];reg trace_on=1;reg [15:0] token,crc;
 reg got_end,got_commit;integer length,pos,kind,index;
 function automatic [7:0] c8(input [7:0] c0,b);
  reg [7:0] c;integer j;begin c=c0^b;for(j=0;j<8;j++)c=c[7]?(c<<1)^7:c<<1;c8=c;end
 endfunction
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;integer j;begin c=c0^{b,8'd0};for(j=0;j<8;j++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 function automatic integer width(input integer k);case(k)0,6:width=2;1,5:width=1;2,4:width=7;3:width=4;default:width=8;endcase endfunction
 task request(input [7:0] cmd,input [15:0] tok,input [7:0] arg);
  integer j;reg [7:0] c;begin tx[0]=cmd;tx[1]=0;tx[2]=tok[15:8];tx[3]=tok[7:0];tx[4]=arg;tx[5]=~arg;c=0;
   for(j=0;j<6;j++)c=c8(c,tx[j]);tx[6]=c;tx[7]=8'ha5;end
 endtask
 task transfer(input integer size);
  integer j,b;begin
   #2000;ss=0;#2000;
   for(j=0;j<size;j++)begin rx[j]=0;for(b=7;b>=0;b--)begin
    mosi=tx[j][b];#190.476;sck=1;rx[j][b]=selected?miso:0;#190.476;sck=0;
   end end
   #2000;ss=1;#2000;
   if(trace_on)begin
    $fwrite(fd,"%0d ",size);for(j=0;j<size;j++)$fwrite(fd,"%02x",tx[j]);$fwrite(fd," ");
    for(j=0;j<size;j++)$fwrite(fd,"%02x",rx[j]);$fwrite(fd,"\n");wirebytes=wirebytes+size;
   end
  end
 endtask
 task status_check;
  integer j;reg [7:0] c;begin c=0;for(j=1;j<7;j++)c=c8(c,rx[j]);
   if(rx[1]!=8'hd6||rx[2][7]||rx[7]!=c)$fatal(1,"status %02x %02x crc %02x/%02x",rx[1],rx[2],rx[7],c);
  end
 endtask
 always @(posedge clk)if(!reset&&av&&ack_ready)begin
  if(!aa||ag!=24)$fatal(1,"bad prepared");acks<=acks+1;
 end
 initial begin
  if(!$value$plusargs("COUNT=%d",count))$fatal(1,"COUNT missing");
  $readmemh("records.hex",records,0,count-1);fd=$fopen("transactions.txt","w");
  #100;reset=0;#(PHASE);
  fork
   begin
    for(n=0;n<count;n++)begin
     if(records[n][95:93]==7&&records[n][76:64]==3)wait(acks==1);
     @(negedge clk);data=records[n];valid=1;
     do @(posedge clk);while(!ready);
     @(negedge clk);valid=0;
    end
   end
   begin
    got_commit=0;
    while(!got_commit)begin
     request(8'hd0,0,0);transfer(8);status_check;
     if(rx[2][0])begin
      token={rx[3],rx[4]};length={rx[5],rx[6]};if(length<1||length>256)$fatal(1,"length");
      for(pos=0;pos<259;pos++)tx[pos]=0;tx[0]=8'hd1;transfer(length+3);
      crc=16'hffff;for(pos=1;pos<=length;pos++)crc=c16(crc,rx[pos]);
      if(crc!={rx[length+1],rx[length+2]})$fatal(1,"block CRC");
      got_end=0;pos=1;
      while(pos<=length)begin
       kind=rx[pos]>>5;index=((rx[pos]&31)<<8)|rx[pos+1];
       if(kind==7&&index==1)got_end=1;if(kind==7&&index==3)got_commit=1;
       pos=pos+4+width(kind);
      end
      if(pos!=length+1)$fatal(1,"split record");
      request(8'hd2,token,0);transfer(8);status_check;
      request(8'hd0,0,0);transfer(8);status_check;
      if({rx[3],rx[4]}!=16'(token+1))$fatal(1,"POP retirement");blocks++;
      if(got_end)begin
       request(8'hd0,0,0);transfer(8);status_check;if(!rx[2][1])$fatal(1,"ACK unavailable");
       request(8'hd3,24,1);transfer(8);status_check;
       request(8'hd0,0,0);transfer(8);status_check;
      end
     end
    end
   end
  join
  $fclose(fd);trace_on=0;if(fault||acks!=1)$fatal(1,"terminal state");
  // Other command families neither select this endpoint nor mutate its state.
  request(8'h60,0,0);transfer(8);if(fault||dut.token!=blocks)$fatal(1,"foreign command");
  // Invalid destructive commands must retain the current token and set fault.
  request(8'hd2,16'hffff,0);transfer(8);if(!fault||dut.token!=blocks)$fatal(1,"invalid POP accepted");
  reset=1;#100;reset=0;#100;
  request(8'hd0,0,0);tx[6]^=1;transfer(8);if(!fault||dut.token!=0)$fatal(1,"bad CRC accepted");
  reset=1;#100;reset=0;#100;
  @(negedge clk);data=records[count-1];valid=1;@(posedge clk);@(negedge clk);valid=0;wait(dut.sealed);
  tx[0]=8'hd1;transfer(2);if(!fault||dut.read_seen||!dut.sealed)$fatal(1,"short READ released block");
  $display("PASS SPI165 records=%0d blocks=%0d wirebytes=%0d phase=%0f",count,blocks,wirebytes,PHASE);$finish;
 end
 initial begin #200000000;$fatal(1,"watchdog");end
endmodule
