// SPDX-License-Identifier: MIT
// Source launch and actual destination capture; no hierarchy force in normal run.
realtime req_launch125=-1,req_capture125=-1,reply_launch125=-1,reply_capture125=-1;
realtime min_req125=1e9,min_reply125=1e9;
integer req_checks125=0,reply_checks125=0,hold_checks125=0;
always @(posedge reset)begin req_launch125=-1;req_capture125=-1;reply_launch125=-1;reply_capture125=-1;end
always @(posedge host_clk)if(dut.h_up)begin
 if(cmd_valid && cmd_ready)begin
  if(req_capture125>=0)begin
   if($realtime-req_capture125<2*qhalf-0.002)$fatal(1,"CDC125 bridge request hold");
   hold_checks125++;
  end
  req_launch125=$realtime;
 end
 if(dut.pending && dut.ack_sync[1]==dut.req_toggle)begin
  if(reply_launch125<0 || $realtime-reply_launch125<4*hhalf-0.002)$fatal(1,"CDC125 bridge reply age");
  if($realtime-reply_launch125<min_reply125)min_reply125=$realtime-reply_launch125;
  reply_capture125=$realtime;reply_checks125++;
 end
end
always @(posedge queue_clk)if(dut.q_up && dut.host_up_q[1])begin
 if(dut.phase==0 && dut.req_sync[1]!=dut.ack_toggle)begin
  if(req_launch125<0 || $realtime-req_launch125<4*qhalf-0.002)$fatal(1,"CDC125 bridge request age");
  if($realtime-req_launch125<min_req125)min_req125=$realtime-req_launch125;
  req_capture125=$realtime;req_checks125++;
 end
 if(dut.phase==2)begin
  if(reply_capture125>=0)begin
   if($realtime-reply_capture125<2*hhalf-0.002)$fatal(1,"CDC125 bridge reply hold");
   hold_checks125++;
  end
  reply_launch125=$realtime;
 end
end
