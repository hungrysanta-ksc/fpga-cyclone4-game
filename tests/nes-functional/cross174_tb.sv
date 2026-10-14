// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module cross174_tb;
reg clk=0;always #5 clk=~clk;
reg reset=1,release_scene=0,ppu_ce=0,rom_fault=0;
reg [8:0] scanline=0,dot=0;
reg bg_low=0,bg_high=0,obj_low=0,obj_high=0,obj_valid=0,extra_sprites=0;
reg [1:0] bg_attribute=0;reg [7:0] obj_attribute=0,obj_x=0;
reg ppu_read=0,ppu_valid=0;reg [13:0] logical_address=0;reg [21:0] physical_address=0;
reg query=0;reg [12:0] query_tile=0;
wire initialized,active,owned,valid,event_valid,response;wire [7:0] errors;
wire [15:0] generation;wire [63:0] event_data;wire [1:0] required_kind;
nes_native_planes165 dut(.*);
integer events=0;reg [63:0] seen;
always @(posedge clk)if(event_valid)begin events=events+1;seen=event_data;end
task pulse;
 begin ppu_ce=1;@(negedge clk);ppu_ce=0;repeat(5)@(negedge clk);end
endtask
task pair(input integer mode);
 begin
  reset=1;@(negedge clk);reset=0;events=0;bg_attribute=0;
  wait(initialized);@(negedge clk);scanline=7;dot=257;pulse();
  scanline=193;dot=228;bg_low=1;ppu_read=1;ppu_valid=1;
  logical_address=14'h150;physical_address=22'h21e150;
  if(mode==7)begin bg_low=0;obj_low=1;obj_valid=1;dot=261;end
  pulse();bg_low=0;obj_low=0;
  dot=232;bg_high=1;logical_address=14'h1ff;physical_address=22'h21e1ff;
  case(mode)
   1:begin logical_address=14'h158;physical_address=22'h21e158;end
   2:begin logical_address=14'h15f;physical_address=22'h21e15f;end
   3:bg_attribute=1;
   4:ppu_valid=0;
   5:begin logical_address[3]=0;physical_address[3]=0;end
   6:physical_address[21:17]=0;
   7:begin bg_high=0;obj_high=1;dot=263;end
  endcase
  pulse();bg_high=0;obj_high=0;obj_valid=0;ppu_read=0;
  scanline=232;dot=1;pulse();wait(owned);@(negedge clk);
  if(mode<=2)begin
   if(!valid || errors || events!=1)$fatal(1,"good pair rejected mode%0d err%h",mode,errors);
   if(mode==0 && (!seen[61] || {seen[60:57],seen[24:16]}!=13'h1e15 || seen[12:0]!=13'h1e1f || seen[55:53]!=0 || seen[15:13]!=7))$fatal(1,"cross descriptor lost source");
   if(mode==1 && seen[63:53]!=0)$fatal(1,"ordinary extension changed");
   if(mode==2 && (seen[61] || !seen[56] || seen[55:53]!=0))$fatal(1,"same tile fine extension");
   for(integer t=0;t<8192;t=t+1)begin
    query=1;query_tile=t;@(negedge clk);
    if(!response || required_kind!==((t==13'h1e15 || (mode==0 && t==13'h1e1f))?2'd1:2'd0))$fatal(1,"required set mode%0d tile%0d",mode,t);
   end
   query=0;
  end else if(valid || !errors[2] || events)$fatal(1,"bad pair admitted mode%0d",mode);
  release_scene=1;@(negedge clk);release_scene=0;query=1;@(negedge clk);
  if(owned || valid || response || required_kind)$fatal(1,"stale lease");query=0;
 end
endtask
reg begin_scene=0,end_scene=0,source_fault=0,c_event=0,c_query=0;
reg [63:0] c_data=0;reg [1:0] query_kind=0;reg [10:0] query_address=0;
wire c_owned,c_valid,c_response,hit;wire [7:0] c_errors,row_count,object_count,exception_count;
wire [5:0] group_count;wire [63:0] data;
nes_native_compact_planes165 compact(.clk(clk),.reset(reset),.release_scene(release_scene),
 .begin_scene(begin_scene),.end_scene(end_scene),.source_fault(source_fault),.event_valid(c_event),.event_data(c_data),
 .query(c_query),.query_kind(query_kind),.query_address(query_address),.owned(c_owned),.valid(c_valid),.errors(c_errors),
 .row_count(row_count),.object_count(object_count),.exception_count(exception_count),.group_count(group_count),.response(c_response),.hit(hit),.data(data));
integer y,x;
initial begin
 repeat(3)@(negedge clk);
 for(integer mode=0;mode<8;mode=mode+1)pair(mode);
 reset=1;@(negedge clk);reset=0;begin_scene=1;@(negedge clk);begin_scene=0;
 for(y=0;y<224;y=y+1)for(x=0;x<33;x=x+1)begin
  c_data=64'd100|((64'(y)&7)<<13)|(64'(y)<<25)|(64'(x)<<33);
  if(y==185 && x==30)c_data=(c_data&~64'h1fff)|64'd200|(64'd1<<61)|(64'd1<<56)|(64'd100<<16);
  c_event=1;@(negedge clk);c_event=0;
  repeat(x==32?36:3)@(negedge clk);
 end
 end_scene=1;@(negedge clk);end_scene=0;wait(c_owned);@(negedge clk);
 if(!c_valid || c_errors || row_count!=224 || exception_count!=1)$fatal(1,"compact err%h rows%0d exceptions%0d",c_errors,row_count,exception_count);
 c_query=1;query_kind=3;query_address=0;@(negedge clk);
 if(!c_response || !hit || data!=((64'd100<<19)|((64'd185*33+30)<<6)|8))$fatal(1,"32bit exception %h",data);
 release_scene=1;@(negedge clk);release_scene=0;@(negedge clk);
 if(hit || c_owned || c_valid)$fatal(1,"compact stale release");
 $display("PASS CROSS174 pairs8 required24576 fullframe7392 exception32 release");$finish;
end
initial begin #10000000;$fatal(1,"watchdog");end
endmodule
