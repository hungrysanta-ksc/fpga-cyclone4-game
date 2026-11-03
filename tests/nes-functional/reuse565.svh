// SPDX-License-Identifier: MIT
// Included inside the actual tile/dual-bank/control testbench.
integer h_edges=0,release_edge,first_free=-1,first_open=-1,consumes565=0;
bit measuring=0;
always @(posedge hc)begin
 h_edges++;
 if(measuring && consume)consumes565++;
 if(measuring && bulk.begin_ready && first_free<0)first_free=h_edges-release_edge;
 if(measuring && bulk.state==bulk.OPEN && bulk.begin_ready && first_open<0)first_open=h_edges-release_edge;
end
task reuse565;
 integer returned;
 bit stale_replay;
 // 48 bytes are sealed and still owned by token 1. Prime only half of
 // the control register and read one byte before aborting this session.
 wait(avail);if(token!=1||length!=48)$fatal(1,"old job");
 bus=24'h400800;rd=0;repeat(6)@(negedge hc);if(oe||rdata!=1)$fatal(1,"partial read");
 rd=1;write_reg(24'h604c,1);write_reg(24'h604d,0);
 @(negedge hc);#1000;reset=1;pv=0;ending=0;gen=953;
 #100;if(avail||!oe||consume||saw_end)$fatal(1,"async abort");
 repeat(6)@(negedge hc);
 #1000;release_edge=h_edges;measuring=1;reset=0;allow=1;
 // As soon as the producer accepts a new plan, fill the same physical bank
 // with different bytes. Do not credit an idle aperture as a usable job.
 plan(0,119,13);wait(done);@(negedge nc);ending=1;do @(posedge nc);while(!er);@(negedge nc);ending=0;
 wait(avail);@(negedge hc);returned=h_edges-release_edge;
 if(length!=16||token!=1||generation!=953||dest!=119||first_free<0||first_open<first_free)$fatal(1,"new ownership");
 stale_replay=$test$plusargs("REPLAY");
 if(stale_replay)begin
  // Before reading even one byte of the new job, replay the entire old ACK.
  ack(1);if(avail||hf565)$fatal(1,"unexpected token namespace behavior");
 end else begin
 for(int i=0;i<16;i++)begin
  bus=24'h400800+i;rd=0;repeat(5)@(negedge hc);if(oe||rdata!=13)$fatal(1,"old data");
 end
 bus=24'h400810;repeat(5)@(negedge hc);if(!oe)$fatal(1,"old tail exposed");rd=1;
 // Remaining halves from the aborted write must not finish the command.
 if($test$plusargs("PARTIAL565"))begin
  write_reg(24'h604e,0);write_reg(24'h604f,0);write_reg(24'h6050,8'ha5);
  repeat(10)@(negedge hc);if(!wrong||!hf565||avail||consume)$fatal(1,"cross-reset assembly");
 end else begin ack(1);if(avail||hf565)$fatal(1,"live ACK");end
 end
 if(consumes565!=($test$plusargs("PARTIAL565")?0:1))$fatal(1,"wrong consume count");
 $display("PASS565 BANK free=%0d open=%0d ready=%0d replay=%0d",first_free,first_open,returned,stale_replay);
 $finish;
endtask
