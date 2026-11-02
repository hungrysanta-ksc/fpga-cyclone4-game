// SPDX-License-Identifier: MIT
// 565's board reset wiring and actual dual-bank / bus control are instantiated by the runner.
integer returns566=0;
always @(posedge hc)if(consume)returns566++;
task offer566(input integer tagbase);
  for(int i=0;i<10;i++)begin plan(1,i,tagbase+i);wait(done);end
  @(negedge nc);ending=1;do @(posedge nc);while(!er);@(negedge nc);ending=0;
  wait(avail);
  if(token!=1||generation!=gen||length!=320||!ck||dest!=0)$fatal(1,"descriptor");
endtask
task read566(input integer tagbase);
  for(int i=0;i<320;i++)begin
    @(negedge hc);bus=24'h400800+i;rd=0;repeat(5)@(negedge hc);
    if(oe||rdata!==((i%32<16)?8'(tagbase+i/32):8'd0))$fatal(1,"read %0d",i);
  end
  rd=1;
endtask
task reset566;
  reset=1;gen=gen+1;#1000;
  if(avail||consume||!oe)$fatal(1,"reset owner");
endtask
task pulse566(input time target,input [23:0] addr,input [7:0] value);
  if(target<$time)$fatal(1,"overlapping strobes");
  #(target-$time);bus=addr;wdata=value;wr=0;repeat(6)@(negedge hc);wr=1;
endtask
