 // Passive host-domain records. All four single-bit sources are registered
 // in the slower NES domain and remain stable for at least one NES cycle.
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [3:0] event_meta,event_sync;
 reg [3:0] event_previous;
 wire [3:0] event_rise=event_sync & ~event_previous;
 reg seen_request,seen_grant,sampled_head;
 reg saw_group,saw_done,saw_end,returned_snapshot;
 wire group_event=event_rise[2],end_event=event_rise[3];
 wire done_event=done_sync[1] && !done_previous;
 wire req_event=event_rise[0] && (!seen_request || group_event);
 wire grant_event=event_rise[1] && (!seen_grant || group_event);
 wire head_event=head_snapshot && !sampled_head;
 // Separate foreground and grant ports can record an immediate grant.
 // A coincident head/grant is written at most one host clock later.
 reg defer_head,port_conflict;
 wire [3:0] writes={end_event,done_event,req_event,group_event};
 wire overlap=(group_event && (req_event || done_event || end_event)) ||
              (req_event && (done_event || end_event)) || (done_event && end_event);
 (* ramstyle="M9K" *) reg [7:0] steps[0:3];
 (* ramstyle="M9K" *) reg [7:0] grants[0:1];
 reg [7:0] step_q,grant_q;
 (* ramstyle="M9K" *) reg [7:0] anchors[0:3];
 reg [7:0] anchor_q;
 wire writer_event=writer!=writer_previous;
 always @(posedge clk) begin
  if(first_e9 || writer_event || query)anchors[first_e9?2:writer_event?0:3]<=now[7:0];
  anchor_q<=anchors[index[1:0]];
  if(|writes) steps[end_event?3:done_event?2:req_event?1:0]<=now[7:0];
  if(grant_event || head_event || defer_head) grants[!grant_event]<=now[7:0];
  // 10=request,11=grant,26=plan,27=done,28=END,29=head E8.
  step_q<=steps[!index[4]?1:index[2]?3:index[0]?2:0];
  grant_q<=grants[index[4]];
 end
 always @(posedge clk) begin
  event_meta<=edge1027;
  event_sync<=event_meta;
  event_previous<=event_sync;
  if(clear_record || first_e9) begin
   seen_request<=0;seen_grant<=0;sampled_head<=0;
   saw_group<=0;saw_done<=0;saw_end<=0;returned_snapshot<=0;
   defer_head<=0;port_conflict<=!clear_record && writer_event;
  end else begin
   defer_head<=grant_event && head_event;
   if(overlap || (defer_head && (grant_event || head_event)))port_conflict<=1;
   if(event_rise[2]) begin
    saw_group<=1;saw_done<=0;saw_end<=0;
    seen_request<=0;seen_grant<=0;
   end
   if(event_rise[0] && (!seen_request || event_rise[2])) begin
    seen_request<=1;
   end
   if(event_rise[1] && (!seen_grant || event_rise[2])) begin
    seen_grant<=1;
   end
   if(done_event)saw_done<=1;
   if(end_event)saw_end<=1;
   // Snapshot uses the pre-edge reader, including on a simultaneous return.
   if(returned) begin sampled_head<=0;returned_snapshot<=sampled_head||head_snapshot;end
   else if(head_snapshot) sampled_head<=1;
  end
 end
