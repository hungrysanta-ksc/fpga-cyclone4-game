# SPDX-License-Identifier: MIT
"""Rejected experiment: STOP can cancel a collector reply and leave query WAIT stuck.
A queued source DONE can also escape after STOP during lease handoff.
Normal schedules and area are measured; this candidate must not be selected.
The failure is intentionally preserved for the replacement-boundary review.
"""
from nes_delta231 import ROOT,once

def apply(d):
 p=d/'nes_core257.sv';s=p.read_text()
 s=once(s,'module nes_core257(', 'module nes_core257(input wire query_ready356,handoff356,')
 s=once(s,'if(q_active)q_pending<=1;', 'if(q_active)begin if(query_ready356)q_pending<=1;end ')
 s=once(s,'(output_phase&&!done)?', '(output_phase&&!done&&!handoff356)?')
 s=once(s,"if(plan_zero319)cursor<=0;\n     else if(plan_step319)cursor<=cursor+13'd1;", '// Plan cursor now belongs to NES query boundary.')
 p.write_text(s,newline='\n')
 p=d/'nes_transport257.sv';s=p.read_text()
 a=s.index(' (* async_reg=');b=s.index(' reg sfault',a)
 s=s[:a]+" reg [1:0] hr;\n always @(posedge host_clk or posedge reset)if(reset)hr<=0;else hr<={hr[0],1'b1};\n wire src_reset=!hr[1],host_reset=!hr[1];\n"+s[b:]
 s=once(s,'reg [1:0] busy,sent,publish;', 'reg [1:0] busy;')
 a=s.index(' reg [39:0] descriptor0');b=s.index(' assign source_empty',a)
 s=s[:a]+""" reg [23:0] descriptor0,descriptor1;
 wire [1:0] block_valid=busy;
 wire [39:0] block0={frame_generation,descriptor0},block1={frame_generation,descriptor1};
 reg pop0,pop1;
 assign source_fault=sfault||hfault;assign host_fault=hfault||sfault;
 wire source_live=hr[1]&&!source_fault&&!abort_source;
"""+s[b:]
 s=s.replace('{frame_generation,length,checksum}','{length,checksum}')
 s=once(s,'publish[bank]<=1;busy[bank]<=1;', 'busy[bank]<=1;')
 s=once(s,'hfault_sync<=0;host_up_sync<=0;sfault<=0;bank<=0;busy<=0;sent<=0;publish<=0;', 'sfault<=0;bank<=0;busy<=0;')
 a=s.index('   hfault_sync<=');b=s.index('   if(source_live)',a)
 s=s[:a]+"   if(abort_source)sfault<=1;\n   if(pop0)busy[0]<=0;if(pop1)busy[1]<=0;\n"+s[b:]
 a=s.index(' reg ack_pending;');b=s.index(' wire [7:0] common_crc',a)
 s=s[:a]+""" reg ack_pending;
 assign ack_valid=ack_pending&&source_live;
 assign ack_accept=1'b1;assign ack_generation=frame_generation;
"""+s[b:]
 s=s.replace('!ack_pending&&ack_send_ready','!ack_pending').replace('sfault_sync<=0;','').replace('ack_data<=0;','')
 s=s.replace('sfault_sync<={sfault_sync[0],sfault};','').replace('ack_pending&&ack_send_ready','ack_pending&&ack_ready&&source_live')
 s=s.replace("ack_data<={1'b1,request_generation};",'')
 s=s.replace('posedge src_clk','posedge host_clk')
 p.write_text(s,newline='\n')
 p=d/'nes_joint257.sv';s=p.read_text()
 s=once(s,'always @(posedge clk)begin aq<=', 'always @(posedge host_clk)begin aq<=')
 s=once(s,'wire raw_response=response,raw_hit=hit;wire [63:0] raw_data=data;', 'wire raw_response,raw_hit;wire [63:0] raw_data;')
 s=once(s,"cf?cf:sf||hf?4'd8:4'd0", "cf?cf:sf||hf||owner_fault356?4'd8:4'd0")
 s=once(s,'assign start_ready=csr&&!fault&&init_sync278[1];', 'assign start_ready=start_send356&&ready_n356[1]&&!fault&&init_sync278[1];')
 # Only encoder instance: validator remains host-clock and independently validates.
 a=s.index('nes_core257 encoder');b=s.index('nes_validator278 validator',a);c=s[a:b]
 c=once(c,'encoder(', 'encoder(.query_ready356(query_ready356),.handoff356(handoff356),')
 for x,y in [('.plan_zero319(plan_zero319)',".plan_zero319(1'b0)"),('.plan_step319(plan_step319)',".plan_step319(1'b0)"),('.plan_cursor319(plan_cursor319)','.plan_cursor319()'),('.query(query)','.query(query_host356)'),('.query_kind(query_kind)','.query_kind(kind_host356)'),('.query_index(query_index)','.query_index(index_host356)'),('.query_generation(query_generation)','.query_generation(generation_host356)'),('.clk(clk)','.clk(host_clk)'),('.start(start&&start_ready)','.start(start_host356&&csr&&query_active356&&init278)'),('.done(done)','.done(done_host356)'),('.v_display_ack(v_display_ack)','.v_display_ack(final_host356)'),('.display_lease(display_lease)','.display_lease(display_h356[1]||final_h356[1])'),('.frame_owned(frame_owned)','.frame_owned(owned_h356[1]||handoff356)'),('.geometry_valid(geometry_valid)','.geometry_valid(geometry_h356[1]||handoff356)')]:c=once(c,x,y)
 s=s[:a]+c+s[b:]
 s=once(s,'.src_clk(clk)', '.src_clk(host_clk)')
 bridge="""
 // Bundled metadata stays immutable under collector/display lease. Only the
 // start notification crosses; no new frame is admitted before final ACK.
 wire start_send356,start_host356,unused_start356,done_host356,done_send356,done_n356,unused_done356;
 wire final_send356,final_host356,unused_final356;
 reg done_pending356,handoff356,final_pending356;
 reg [1:0] final_h356;
 reg [1:0] ready_n356,owned_h356,geometry_h356,display_h356,phase_n356;
 wire query_host356,query_ready356,query_active356,query_drained356,owner_fault356;
 wire [2:0] kind_host356;wire [12:0] index_host356;wire [15:0] generation_host356;
 wire [31:0] query_data356;wire [64:0] response356;
 nes_native_mailbox206 #(.WIDTH(1)) start356(clk,host_clk,reset,start&&start_ready,start_send356,1'b1,
  start_host356,csr&&query_active356&&init278,unused_start356);
 nes_native_mailbox206 #(.WIDTH(1)) done356(host_clk,clk,reset,done_pending356,done_send356,1'b1,
  done_n356,1'b1,unused_done356);
 nes_native_mailbox206 #(.WIDTH(1)) final356(clk,host_clk,reset,v_display_ack,final_send356,1'b1,
  final_host356,1'b1,unused_final356);
 assign done=done_n356;
 always @(posedge clk or posedge reset)if(reset)begin ready_n356<=0;phase_n356<=0;final_pending356<=0;end
 else begin if(v_display_ack)final_pending356<=1;else if(start&&start_ready)final_pending356<=0;ready_n356<={ready_n356[0],csr&&query_active356};phase_n356<={phase_n356[0],output_phase};end
 always @(posedge host_clk or posedge reset)if(reset)begin
  final_h356<=0;owned_h356<=0;geometry_h356<=0;display_h356<=0;done_pending356<=0;handoff356<=0;
 end else begin
  final_h356<={final_h356[0],final_pending356};owned_h356<={owned_h356[0],frame_owned};geometry_h356<={geometry_h356[0],geometry_valid};display_h356<={display_h356[0],display_lease};
  if(done_pending356&&done_send356)done_pending356<=0;
  if(done_host356)begin done_pending356<=1;handoff356<=1;end
  if(display_h356[1]||cancel)handoff356<=0;
 end
 nes_query355 query356(host_clk,clk,reset,cancel,query_drained356&&!cancel,
  query_drained356,query_active356,query_host356,query_ready356,{kind_host356,index_host356,generation_host356},
  raw_response,1'b1,response356,query,query_data356,response,hit,data,
  phase_n356[1],plan_zero319,plan_step319,plan_cursor319,owner_fault356);
 assign {query_kind,query_index,query_generation}=query_data356;
 assign {raw_hit,raw_data}=response356;
"""
 cut=bridge.index(' nes_native_mailbox206')
 s=once(s,' wire [7:0] ram_a_q',bridge[:cut]+'\n wire [7:0] ram_a_q')
 s=once(s,'wire record_last319;',bridge[cut:]+'\nwire record_last319;')
 # Include boundary in an existing compilation unit so all inherited file lists bind it.
 s+='\n'+(ROOT/'tools/nes_query355.sv').read_text()
 p.write_text(s,newline='\n')
