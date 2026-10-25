# SPDX-License-Identifier: MIT
"""Diagnostic repair of rejected356 cancellation boundary. Not selected338 or NES executor replacement."""
from nes_delta231 import once

def apply(d,board=False):
 p=d/'nes_native_frame201.sv';s=p.read_text()
 s=once(s,' input wire clk,reset,release_frame,ppu_ce,rom_fault,',' output reg collector_cancel358,\n input wire clk,reset,release_frame,ppu_ce,rom_fault,')
 s=once(s,' always @(posedge clk)begin\n  response<=0;', ''' // Registered after a release edge cleared every collector member.
 always @(posedge clk)begin
  if(reset)collector_cancel358<=1;
  else if(start)collector_cancel358<=0;
  else if(release_frame&&!owned&&!joining&&!response&&
    !fetch_owned&&!compact_owned&&!raster_owned&&!patch_owned&&
    !fetch_response&&!compact_response&&!raster_response&&!patch_response)collector_cancel358<=1;
 end
 always @(posedge clk)begin
  response<=0;''');p.write_text(s,newline='\n')
 p=d/'nes_joint266.sv';s=p.read_text();name='nes_joint267_board' if board else 'nes_joint266';s=once(s,'module '+name+' #(parameter SHARED=1)(', 'module '+name+' #(parameter SHARED=1)(input wire collector_cancel358,')
 s=once(s,'nes_joint257 core(', 'nes_joint257 core(.collector_cancel358(collector_cancel358),');p.write_text(s,newline='\n')
 p=d/'nes_joint257.sv';s=p.read_text();s=once(s,'module nes_joint257(', 'module nes_joint257(input wire collector_cancel358,')
 s=once(s,'assign done=done_n356;', 'assign done=done_n356&&!cancel;')
 s=once(s,'if(done_host356)begin done_pending356<=1;handoff356<=1;end', 'if(done_host356&&!cancel)begin done_pending356<=1;handoff356<=1;end\n  if(cancel)done_pending356<=0;')
 s=once(s,'done_pending356,done_send356,1\'b1', "done_pending356&&!cancel,done_send356,1'b1")
 s=once(s,'nes_query355 query356(host_clk,clk,reset,cancel,', 'nes_query355 query356(collector_cancel358,host_clk,clk,reset,cancel,')
 s=once(s,'module nes_query355(', 'module nes_query355(input wire collector_cancel358,')
 s=once(s,'wire nes_drained=stop_n[1]&&stop_applied', 'wire nes_drained=stop_n[1]&&stop_applied&&collector_cancel358')
 s=once(s,'WAIT:if(response)begin', 'WAIT:if(stop_n[1]&&collector_cancel358)begin result<=0;ns<=SEND;end else if(response)begin')
 # A cancelled request still returns one discarded mailbox reply, retiring host busy.
 p.write_text(s,newline='\n')
 if board:
  p=d/'nes_native_capture201.sv';s=once(p.read_text(),'module nes_native_capture201(', 'module nes_native_capture201(output wire collector_cancel358,');p.write_text(s,newline='\n')
  p=d/'nes_live_joint.sv';s=p.read_text();s=once(s,'nes_native_capture201 native_frame(', 'wire collector_cancel358;\nnes_native_capture201 native_frame(.collector_cancel358(collector_cancel358),')
  import re
  s,n=re.subn(r'(nes_joint267_board\s+(?:#\([^\n]+?\)\s*)?\w+\s*\()',r'\1.collector_cancel358(collector_cancel358),',s);assert n==1,n
  p.write_text(s,newline='\n');return
 p=d/'joint266_tb.sv';s=p.read_text();s=once(s,' wire exporter_release;wire release_frame;', ' wire collector_cancel358;wire exporter_release;wire release_frame;')
 s=once(s,'nes_joint266 dut(', 'nes_joint266 dut(.collector_cancel358(collector_cancel358),')
 s=once(s,' task clear_output;', ''' always @(posedge clk)if(!reset&&collector_cancel358)begin
  if(frame.owned||frame.response||frame.joining||frame.fetch_owned||frame.compact_owned||frame.raster_owned||frame.patch_owned)
   $fatal(1,"collector cancelled ACK before drain358");
 end
 task clear_output;''');p.write_text(s,newline='\n')
