// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module context375_tb;
 parameter CASE=0;
 reg clk=0;always #5.952381 clk=~clk;
 reg [7:0] progress375=0;reg reset=1,active=0,hs=0,put=0,check=0;reg [5:0] pa=0;reg [7:0] pd=0,op=14;reg [31:0] expected=32'h89abcdef;
 wire ready,hbusy,hdone,fv,cbusy,cdone,fault,rw;wire [3:0] fa;wire [7:0] qa,rd;wire [5:0] ra;
 reg [7:0] qdata,rq;reg [7:0] packet[0:255],memory[0:1023];
 nes_host_context375 dut(.clk(clk),.reset(reset),.active(active),.cursor375(progress375),.header_start(hs),.header_op(op),.queue_data(qdata),
 .ready(ready),.header_busy(hbusy),.header_done(hdone),.field_valid(fv),.field_at(fa),.queue_address(qa),
 .put_valid(put),.put_address(pa),.put_data(pd),.check_start(check),.expected_token(expected),.check_busy(cbusy),.check_done(cdone),.fault(fault),
 .ram_address(ra),.ram_write(rw),.ram_data(rd),.ram_q(rq));
 integer fields=0,writes=0;reg clear=0;integer cursor=512;
 always @(posedge clk)begin
  if(reset||!active)progress375<=0;
  else if((hs||check)&&ready)progress375<=0;
  else if(hbusy||cbusy)begin if(hdone||cdone)progress375<=0;else progress375<=progress375+1'b1;end
  qdata<=packet[qa];rq<=memory[716+ra];
  if(rw)begin if(!active||ra>=52)$fatal(1,"context aperture bound");memory[716+ra]<=rd;writes++;end
  if(clear)begin
   memory[cursor]<=0;
   if(cursor==1023)clear<=0;else cursor<=cursor==677?768:cursor+1;
  end
  if(fv)begin
   if(fa!=fields||qdata!==packet[fa<4?fa:fa+6])$fatal(1,"header progression field%0d expected%0d",fa,fields);
   fields++;
  end
 end
 task tick;begin @(negedge clk);end endtask
 task header(input [7:0] kind);
 begin fields=0;op=kind;wait(ready);tick();hs=1;tick();hs=0;wait(hdone);repeat(2)tick();if(fields!=(kind==14?15:kind==12?14:10))$fatal(1,"header count");end endtask
 task verify;
 begin wait(ready);tick();check=1;tick();check=0;wait(cdone||fault);repeat(2)tick();end endtask
 initial begin
  for(integer i=0;i<256;i++)packet[i]=i;
  packet[16]=8'hef;packet[17]=8'hcd;packet[18]=8'hab;packet[19]=8'h89;
  repeat(4)tick();reset=0;repeat(4)tick();
  if(ready||rw)$fatal(1,"before init278");active=1;
  header(14);
  if(CASE>=1&&CASE<=4)memory[724+CASE-1]=memory[724+CASE-1]^8'h01;
  if(CASE==5)begin header(2);end // New header invalidates all cold token lanes.
  if(CASE==6)begin
   wait(ready);put=1;pa=52;tick();put=0;
  end else if(CASE==7)begin
   wait(ready);check=1;tick();check=0;wait(cbusy);active=0;repeat(10)tick();
   if(ready||rw||cdone||fv)$fatal(1,"STOP/fault allowed completion");
   $display("PASS CONTEXT375 case=7");$finish;
  end else begin
   // Actual frame-clear traversal owns port B; token context must survive it.
   clear=1;verify();wait(!clear);
  end
  if(CASE==0)begin
   if(fault||memory[724]!=8'hef||memory[727]!=8'h89)$fatal(1,"token compare or frame clear");
   header(7);
   for(integer i=0;i<4;i++)begin wait(ready);pa=8+i;pd=expected[i*8+:8];put=1;tick();put=0;tick();end
   verify();if(fault)$fatal(1,"tile token store/verify");
   header(12);verify();if(fault)$fatal(1,"single-range token");
  end else begin
   if(!fault)$fatal(1,"bad token/context accepted case%0d",CASE);
   begin integer saved;saved=writes;repeat(20)tick();if(writes!=saved||ready||rw||cdone)$fatal(1,"RAM mutated after fault");end
  end
  $display("PASS CONTEXT375 case=%0d",CASE);$finish;
 end
 initial begin #200000;$fatal(1,"context375 timeout case%0d mode%0d",CASE,dut.mode);end
endmodule
