// MCU-owned whole-operation lock. Commands: 1 capture, 2 restore,
// 3 commit restored output, 0 release/cancel (never releases partial restore).
module gbc_state_session # (parameter TIMEOUT_BITS=22)(
 input wire clk,reset,command_valid,input wire[7:0]command,
 input wire menu_active,safe_boundary,core_quiet,io_busy,
 input wire cap_accept,cap_response,audio_accept,audio_response,
 input wire output_drained,capture_armed,
 output wire locked,seek_boundary,hold_core,access_ready,write_allowed,
 output wire drain_outputs,reset_outputs,start_capture,
 output wire[7:0]status,input wire watchdog_tick);
 localparam IDLE=0,SEEK=1,HOLD=2,RESTORE=3,DRAIN=4,FLUSH=5,ARM=6,READY=7,FAILED=8;
 reg[3:0]phase;reg restoring,error,cap_pending,audio_pending;
 reg[1:0]timer;reg[6:0]settle;
 assign locked=phase!=IDLE;
 assign seek_boundary=phase==SEEK;
 assign hold_core=locked&&!seek_boundary;
 assign access_ready=core_quiet&&((phase==HOLD&&safe_boundary)||phase==RESTORE||phase==READY);
 assign write_allowed=core_quiet&&phase==RESTORE;
 assign drain_outputs=phase==DRAIN||phase==FLUSH||(phase==FAILED&&restoring);
 assign reset_outputs=phase==FLUSH;
 assign start_capture=phase==ARM&&settle==0;
 assign status={error,phase==READY,1'b0,write_allowed,restoring,locked,locked&&!access_ready,access_ready};
 always @(posedge clk)begin
  if(reset)begin phase<=IDLE;restoring<=0;error<=0;cap_pending<=0;audio_pending<=0;timer<=0;settle<=0;end
  else begin
   if(cap_accept)cap_pending<=1;
   if(cap_response)cap_pending<=0;
   if(audio_accept)audio_pending<=1;
   if(audio_response)audio_pending<=0;
   if(phase==SEEK||phase==DRAIN||phase==ARM)begin
    if(watchdog_tick)begin
     if((&timer))begin phase<=FAILED;error<=1;end else timer<={timer[0],1'b1};
    end
   end else timer<=0;
   case(phase)
    SEEK:if(safe_boundary)begin phase<=HOLD;timer<=0;end
    HOLD:if(core_quiet&&!safe_boundary)phase<=SEEK; // Last CPU cycle may start DMA.
    DRAIN:begin
     if(cap_pending||audio_pending||cap_accept||audio_accept||!output_drained||io_busy)settle<=0;
     else if(settle==63)begin phase<=FLUSH;settle<=0;timer<=0;end
     else settle<=settle+1'b1;
    end
    FLUSH:if(settle==63)begin phase<=ARM;settle<=0;end else settle<=settle+1'b1;
    ARM:begin
     if(settle!=127)settle<=settle+1'b1;
     if(capture_armed&&settle>=8)begin phase<=READY;timer<=0;end
    end
   endcase
   if(command_valid)begin
    if(io_busy)error<=1;
    else case(command)
     0:if(phase==IDLE||phase==SEEK||phase==HOLD||phase==READY||(phase==FAILED&&!restoring))begin phase<=IDLE;restoring<=0;error<=0;timer<=0;settle<=0;end else error<=1;
     1:if(phase==IDLE&&menu_active)begin phase<=SEEK;error<=0;restoring<=0;timer<=0;end else error<=1;
     2:if(phase==IDLE&&menu_active)begin phase<=RESTORE;error<=0;restoring<=1;timer<=0;end else error<=1;
     3:if(phase==RESTORE&&core_quiet)begin phase<=DRAIN;settle<=0;timer<=0;end else error<=1;
     default:error<=1;
    endcase
   end
  end
 end
endmodule
