
module nes_plan_path267(
 input wire prelease361,input wire [31:0] epoch361,serial361,
 input wire [9:0] plan_cursor319,output wire plan_zero319,plan_step319,output wire plan_admit319,input wire [113:0] link270,output wire [199:0] status270,output wire crc_take270,

 input wire clk,host_clk,reset,stop,lease,retire_permitted,
 input wire source_ready,source_is_rom,source_writing,input wire [31:0] captured_epoch,live_epoch,
 output wire retire_commit,core_error267,output wire [21:0] core_response_address267,
 input wire [15:0] generation,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire selected,miso,
 input wire tile_closed,output wire tv,input wire tr,output wire [7:0] td,
 output wire [4:0] ti,output wire [5:0] tl,output wire [1:0] tk,output wire [9:0] ts,
 output wire ev,ep295,input wire er,
 input wire qualified,core_safe,core_request,input wire [21:0] core_address,
 output wire core_ready,core_response,output wire [7:0] core_data,
 input wire mem_ready,mem_response,mem_error,input wire [21:0] mem_response_address,input wire [7:0] mem_data,
 output wire mem_request,output wire [21:0] mem_address,output wire fault,drained,retire_done
);
 wire ha361,hr361,hready361,hresponse361,herror361,hfault361,hbusy361,hfinished361;wire [21:0] haddr361;
 nes_hint361 hint(.host_clk(host_clk),.clk(clk),.reset(reset),.stop(stop),.prelease(prelease361),.display_lease(lease),
 .immutable(source_ready&&source_is_rom&&!source_writing&&captured_epoch==live_epoch),.generation(generation),.epoch(epoch361),.serial(serial361),.link(link270),
 .active(ha361),.request(hr361),.address(haddr361),.ready(hready361),.response(hresponse361),.error(herror361),.fault(hfault361),.busy(hbusy361),.finished(hfinished361));
 wire pw,pr,seal,idle,retire,done,ef,bf,sf,pv,pready,tdone;
 wire [7:0] pd,mask,am;wire [9:0] plen,slot;wire [4:0] pcount;
 wire [15:0] crc,pg,eg,tg;wire [1:0] kind;wire [12:0] tag;wire [47:0] rows;wire [103:0] tags;
 reg closed_q;always @(posedge host_clk)if(reset||stop)closed_q<=0;else closed_q<=tile_closed;
 nes_plan_spi200 endpoint(.admit319(plan_admit319),.link270(link270),.status270(status270),.crc_take270(crc_take270),.clk(host_clk),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(sf||bf),
  .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.selected(selected),.miso(miso),.fault(ef),
  .plan_idle(idle),.plan_ready(pr),.plan_write(pw),.plan_data(pd),.plan_seal(seal),.plan_length(plen),.plan_plans(pcount),.plan_crc(crc),
  .retire_done(retire_done),.retire(retire),.end_generation(generation),
  .chunk_ready(1'b0),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),.chunk_generation(16'd0),.chunk_token(32'd0),
  .end_sealed(tile_closed&&!closed_q));
 nes_plan_batch206 #(.SHARED_CRC307(1)) transport(.plan_cursor319(plan_cursor319),.plan_zero319(plan_zero319),.plan_step319(plan_step319),.host_clk(host_clk),.nes_clk(clk),.reset(reset),.active(1'b1),.stop(stop),.source_fault(ef||sf),
  .write_valid(pw),.write_ready(pr),.write_data(pd),.retire(retire),.retire_done(retire_done),.retire_permitted(retire_permitted),.retire_commit(retire_commit),
  .seal(seal),.seal_length(plen),.seal_plans(pcount),.seal_crc(crc),.host_idle(idle),.fault(bf),.lease_valid(lease),.lease_generation(generation),
  .plan_valid(pv),.plan_ready(pready),.tile_done(tdone),.plan_kind(kind),.plan_generation(pg),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),
  .plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(tags),.end_valid(ev),.end_partial295(ep295),.end_ready(er),.end_generation(eg));
 wire mr,mready,mresponse,merror;wire [21:0] ma,mra,cra;wire [7:0] md;wire ce;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) source(.hint_active361(ha361),.hint_request361(hr361),.hint_owner361(prelease361),.hint_address361(haddr361),.hint_ready361(hready361),.hint_response361(hresponse361),.hint_error361(herror361),.clk(clk),.reset(reset),.stop(stop),.frame_owned(lease),.geometry_valid(lease),.frame_generation(generation),
  .source_ready(source_ready),.source_is_rom(source_is_rom),.source_writing(source_writing),.captured_epoch(captured_epoch),.live_epoch(live_epoch),
  .plan_valid(pv),.plan_ready(pready),.plan_kind(kind),.plan_generation(pg),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(tags),
  .qualified_slot(qualified),.core_safe(core_safe),.core_request(core_request),.core_address(core_address),.core_ready(core_ready),.core_response(core_response),.core_error(ce),.core_response_address(cra),.core_data(core_data),
  .mem_ready(mready),.mem_response(mresponse),.mem_error(merror),.mem_response_address(mra),.mem_data(md),.mem_request(mr),.mem_address(ma),
  .out_valid(tv),.out_ready(tr),.out_data(td),.out_index(ti),.out_length(tl),.out_kind(tk),.out_slot(ts),.out_generation(tg),.busy(),.done(tdone),.fault(sf),.drained(drained));
 assign mem_request=mr;assign mem_address=ma;
 assign mready=mem_ready;assign mresponse=mem_response;assign merror=mem_error;assign mra=mem_response_address;assign md=mem_data;
 assign core_error267=ce;assign core_response_address267=cra;
 assign fault=ef||bf||sf||ce||hfault361;
endmodule


module nes_hint361(input wire host_clk,clk,reset,stop,prelease,display_lease,immutable,
 input wire [15:0] generation,input wire [31:0] epoch,serial,input wire [113:0] link,
 output wire active,request,output wire [21:0] address,input wire ready,response,error,
 output reg fault,output wire busy,output reg finished);
 reg [111:0] tags;reg invalid,used,launch,receiving;reg [1:0] complete_sync,launch_sync,pre_sync,display_sync;
 reg complete;reg [6:0] cursor;reg pending,running;
 wire [7:0] command=link[32:25],incoming=link[24:17];
 wire [9:0] count=link[16:7];wire byte_event=link[110];
 wire ending=link[109]&&command==8'hea&&count==28;
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
     1:if(incoming!=7)invalid<=1;
     2:if(incoming!=generation[7:0])invalid<=1;
     3:if(incoming!=generation[15:8])invalid<=1;
     4,5,6,7:if(incoming!=epoch[(count-4)*8+:8])invalid<=1;
     8,9,10,11:if(incoming!=serial[(count-8)*8+:8])invalid<=1;
     default:;
    endcase
    if(count>=12&&count<26)begin
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
     if(error||cursor==111)begin running<=0;complete<=launch_sync[1];finished<=!error;end
     else cursor<=cursor+1'b1;
    end
   end
  end
 end
endmodule
