# SPDX-License-Identifier: MIT
"""Shared SPI EA extended packet and private five-tag ROM job, no DMA authority."""
from nes_delta231 import once
from nes_cache360 import apply as cache

MODULE=r'''
module nes_hint361(input wire host_clk,clk,reset,stop,prelease,display_lease,immutable,
 input wire [15:0] generation,input wire [31:0] epoch,serial,input wire [113:0] link,
 output wire active,request,output wire [21:0] address,input wire ready,response,error,
 output reg fault,output wire busy,output reg finished);
 reg [79:0] tags;reg invalid,used,launch,receiving;reg [1:0] complete_sync,launch_sync,pre_sync,display_sync;
 reg complete;reg [6:0] cursor;reg pending,running;
 wire [7:0] command=link[32:25],incoming=link[24:17];
 wire [9:0] count=link[16:7];wire byte_event=link[110];
 wire ending=link[109]&&command==8'hea&&count==24;
 wire owner=(prelease||display_lease)&&immutable;
 wire host_owner=pre_sync[1]&&!display_sync[1]&&immutable;
 assign busy=launch!=complete_sync[1];
 assign active=running&&owner&&!stop&&!fault;
 assign request=active&&!pending;
 assign address=22'h200000+{5'd0,tags[(cursor[6:4]*16)+:13],4'b0}+cursor[3:0];
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin tags<=0;invalid<=0;used<=0;launch<=0;complete_sync<=0;pre_sync<=0;display_sync<=0;receiving<=0;fault<=0;end
  else if(stop)begin invalid<=0;used<=0;launch<=0;complete_sync<=0;pre_sync<=0;display_sync<=0;receiving<=0;fault<=0;end
  else begin
   pre_sync<={pre_sync[0],prelease};display_sync<={display_sync[0],display_lease};complete_sync<={complete_sync[0],complete};
   if(!pre_sync[1])used<=0;
   if(byte_event&&count==0)begin invalid<=0;receiving<=incoming==8'hea&&host_owner&&!busy&&!used;end
   if(byte_event&&command==8'hea)begin
    case(count)
     1:if(incoming!=5)invalid<=1;
     2:if(incoming!=generation[7:0])invalid<=1;
     3:if(incoming!=generation[15:8])invalid<=1;
     4,5,6,7:if(incoming!=epoch[(count-4)*8+:8])invalid<=1;
     8,9,10,11:if(incoming!=serial[(count-8)*8+:8])invalid<=1;
     default:;
    endcase
    if(count>=12&&count<22)begin
     if(!host_owner||busy||used)invalid<=1;
     else tags[(count-12)*8+:8]<=incoming;
     if(count[0]&&incoming[7:5]!=0)invalid<=1;
    end
   end
   if(ending)begin
    receiving<=0;
    if(!receiving||invalid||!link[108]||!host_owner||busy||used)fault<=1;
    else begin launch<=!launch;used<=1;end
   end
  end
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin complete<=0;launch_sync<=0;cursor<=0;pending<=0;running<=0;finished<=0;end
  else if(stop)begin complete<=0;launch_sync<=0;cursor<=0;pending<=0;running<=0;finished<=0;end
  else begin
   launch_sync<={launch_sync[0],launch};finished<=0;
   if(!owner||fault)begin running<=0;pending<=0;complete<=launch_sync[1];end
   else if(!running&&launch_sync[1]!=complete)begin cursor<=0;pending<=0;running<=1;end
   else if(running)begin
    if(request&&ready)pending<=1;
    if(pending&&response)begin
     pending<=0;
     if(error||cursor==79)begin running<=0;complete<=launch_sync[1];finished<=!error;end
     else cursor<=cursor+1'b1;
    end
   end
  end
 end
endmodule
'''

def apply(d,board=False):
 cache(d)
 p=d/'nes_spi270.sv';s=p.read_text()
 s=once(s,"command==8'hea ? (count==7&&crc_good280&&tail_good280):1'b0)","command==8'hea ? ((count==7&&crc_good280&&tail_good280)||(count==24&&request_value280==payload_crc280)):1'b0)")
 s=once(s,"if((count==0&&incoming==8'he1)||command==8'he1||plan_payload314)","if((count==0&&(incoming==8'he1||incoming==8'hea))||command==8'he1||plan_payload314||(command==8'hea&&count<22))")
 s=once(s,"5:crc_good280<=incoming==request_crc;6:tail_good280<=incoming==8'ha5;", "5:crc_good280<=incoming==request_crc;6:tail_good280<=incoming==8'ha5;\n     22:request_value280[7:0]<=incoming;23:request_value280[15:8]<=incoming;")
 p.write_text(s,newline='\n')
 p=d/'nes_plan_spi200.sv';s=p.read_text();s=once(s,"else if(command==8'hea)begin\n      if(!live", "else if(command==8'hea&&count==24)begin\n      if(!live||ended||retiring||!plan_idle||!link270[108])fault<=1;\n     end else if(command==8'hea)begin\n      if(!live")
 p.write_text(s,newline='\n')
 # Reuse the normal tile/cache/arbiter ports. Hint owns only private reads.
 p=d/'nes_source_tile192.sv';s=p.read_text();s=once(s,' input wire clk,reset,stop,frame_owned,geometry_valid,',' input wire hint_active361,hint_request361,hint_owner361,input wire [21:0] hint_address361,output wire hint_ready361,hint_response361,hint_error361,\n input wire clk,reset,stop,frame_owned,geometry_valid,')
 s=once(s,' assign plan_ready=ready_internal&&!fault;', ' assign plan_ready=ready_internal&&!fault&&!hint_active361;')
 s=once(s,' wire arb_request,arb_abort,arb_ready,arb_idle,arb_response,arb_error;', ''' wire cache_ready361,cache_response361,cache_error361;
 assign tile_ready=cache_ready361&&!hint_active361;assign tile_response=cache_response361&&!hint_active361;assign tile_error=cache_error361;
 assign hint_ready361=cache_ready361&&hint_active361;assign hint_response361=cache_response361&&hint_active361;assign hint_error361=cache_error361;
 wire arb_request,arb_abort,arb_ready,arb_idle,arb_response,arb_error;''')
 s=once(s,'.flush(tile_cancel||denied||!immutable)', '.flush(stop||denied||tile_fault||!immutable||(!hint_owner361&&!lease))')
 s=once(s,'.request(tile_request),.address({5\'h10,tile_address}),.generation(tile_generation)', ".request(hint_active361?hint_request361:tile_request),.address(hint_active361?hint_address361:{5'h10,tile_address}),.generation(hint_active361?frame_generation:tile_generation)")
 s=once(s,'.ready(tile_ready),.idle(tile_idle),.response(tile_response),.error(tile_error)', '.ready(cache_ready361),.idle(tile_idle),.response(cache_response361),.error(cache_error361)')
 s=s.replace('assign tile_ready=arb_ready;assign tile_idle=arb_idle;assign tile_response=arb_response;assign tile_error=arb_error;','assign cache_ready361=arb_ready;assign tile_idle=arb_idle;assign cache_response361=arb_response;assign cache_error361=arb_error;')
 s=once(s,'.plan_valid(plan_valid&&!fault)', '.plan_valid(plan_valid&&!fault&&!hint_active361)')
 p.write_text(s,newline='\n')
 name='nes_plan_path267.sv' if board else 'nes_plan_rom267.sv'
 p=d/name;s=p.read_text();s=once(s,' input wire [9:0] plan_cursor319,',' input wire prelease361,input wire [31:0] epoch361,serial361,\n input wire [9:0] plan_cursor319,')
 extra=''' wire ha361,hr361,hready361,hresponse361,herror361,hfault361,hbusy361,hfinished361;wire [21:0] haddr361;
 nes_hint361 hint(.host_clk(host_clk),.clk(clk),.reset(reset),.stop(stop),.prelease(prelease361),.display_lease(lease),
 .immutable(IMMUTABLE361),.generation(generation),.epoch(epoch361),.serial(serial361),.link(link270),
 .active(ha361),.request(hr361),.address(haddr361),.ready(hready361),.response(hresponse361),.error(herror361),.fault(hfault361),.busy(hbusy361),.finished(hfinished361));
'''.replace('IMMUTABLE361','source_ready&&source_is_rom&&!source_writing&&captured_epoch==live_epoch' if board else "1'b1")
 s=once(s,' wire pw,pr,seal,idle,retire,done,ef,bf,sf,pv,pready,tdone;',extra+' wire pw,pr,seal,idle,retire,done,ef,bf,sf,pv,pready,tdone;')
 s=once(s,' source(.clk(clk)', ' source(.hint_active361(ha361),.hint_request361(hr361),.hint_owner361(prelease361),.hint_address361(haddr361),.hint_ready361(hready361),.hint_response361(hresponse361),.hint_error361(herror361),.clk(clk)')
 s=s.replace('assign fault=ef||bf||sf||ce;', 'assign fault=ef||bf||sf||ce||hfault361;').replace('assign fault=ef||bf||sf||core_error267;', 'assign fault=ef||bf||sf||core_error267||hfault361;')
 p.write_text(s+'\n'+MODULE,newline='\n')
