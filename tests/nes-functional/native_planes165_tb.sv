// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
// Replay same-edge PPU observations at their original NES-clock intervals.
// The new collector directly drives the bounded producer in this test.
module native_planes165_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_scene=0,ppu_ce=0,rom_fault=0;
 reg [8:0] scanline=0,dot=0;
 reg bg_low=0,bg_high=0,obj_low=0,obj_high=0,obj_valid=0,extra_sprites=0;
 reg [1:0] bg_attribute=0;reg [7:0] obj_attribute=0,obj_x=0;
 reg ppu_read=0,ppu_valid=0;reg [13:0] logical_address=0;reg [21:0] physical_address=0;
 reg query=0;reg [12:0] query_tile=0;
 wire initialized,active,owned,valid,event_valid,response;
 wire [7:0] errors;wire [15:0] generation;wire [63:0] event_data;wire [1:0] required_kind;
 nes_native_planes165 dut(.*);
 wire old_owned,old_valid,old_event;wire [7:0] old_errors;wire [63:0] old_word;
 nes_native_fetch165 baseline(.clk(clk),.reset(reset),.release_scene(release_scene),.ppu_ce(ppu_ce),.rom_fault(rom_fault),
  .scanline(scanline),.dot(dot),.bg_low(bg_low),.bg_high(bg_high),.obj_low(obj_low),.obj_high(obj_high),
  .obj_valid(obj_valid),.extra_sprites(extra_sprites),.bg_attribute(bg_attribute),.obj_attribute(obj_attribute),.obj_x(obj_x),
  .ppu_read(ppu_read),.ppu_valid(ppu_valid),.logical_address(logical_address),.physical_address(physical_address),
  .query(1'b0),.query_tile(13'd0),.owned(old_owned),.valid(old_valid),.errors(old_errors),.event_valid(old_event),.event_data(old_word));
 reg compact_query=0;reg [1:0] query_kind=0;reg [10:0] query_address=0;
 wire compact_owned,compact_valid,compact_response,hit;wire [7:0] compact_errors,row_count,object_count,exception_count;
 wire [5:0] group_count;wire [63:0] data;
 reg old_owner=0;
 nes_native_compact_planes165 compact(.clk(clk),.reset(reset),.release_scene(release_scene),
  .begin_scene(dut.begin_frame),.end_scene(owned&&!old_owner),.source_fault(owned&&!valid),
  .event_valid(event_valid),.event_data(event_data),.query(compact_query),.query_kind(query_kind),.query_address(query_address),
  .owned(compact_owned),.valid(compact_valid),.errors(compact_errors),.row_count(row_count),.object_count(object_count),
  .exception_count(exception_count),.group_count(group_count),.response(compact_response),.hit(hit),.data(data));
 integer input_file,output_file,event_file,old_file,dummy,frame,tick,last_tick,mode,index,k;
 integer low_bg,high_bg,low_obj,high_obj,obj_ok,extra,attr,read_ok,valid_ok,scan,dot_in;
 reg [7:0] oattr,ox,byte_value;reg [13:0] logical_in;reg [21:0] physical_in;
 string source_name,output_name;
 reg [1:0] expected_set[0:8191];
 reg injected=0;
 always @(posedge clk)begin
  old_owner<=owned;
  if(event_valid)begin
   $fwrite(event_file,"%016h\n",event_data);
   expected_set[event_data[12:0]]=expected_set[event_data[12:0]]|(event_data[49]?2:1);
  end
  if(old_event)$fwrite(old_file,"%016h\n",old_word);
 end
 task read_item(input integer kind,input integer address,input bit expected);
  begin
   @(negedge clk);compact_query=1;query_kind=kind;query_address=address;
   @(negedge clk);
   if(compact_response!==1 || hit!==expected || (!expected && data!==0))$fatal(1,"sealed query contract");
   if(expected)$fwrite(output_file,"%0d %0d %016h\n",kind,address,data);
   compact_query=0;
  end
 endtask
 initial begin
  dummy=$value$plusargs("INPUT=%s",source_name);dummy=$value$plusargs("OUTPUT=%s",output_name);
  dummy=$value$plusargs("MODE=%d",mode);if(!dummy)mode=0;
  input_file=$fopen(source_name,"r");output_file=$fopen(output_name,"w");
  event_file=$fopen({output_name,".events"},"w");old_file=$fopen({output_name,".old"},"w");
  if(!input_file || !output_file)$fatal(1,"missing replay file");
  for(index=0;index<8192;index=index+1)expected_set[index]=0;
  repeat(3)@(negedge clk);reset=0;wait(initialized);@(negedge clk);
  last_tick=-1;
  while(!$feof(input_file))begin
   dummy=$fscanf(input_file,"%d %d %d %d %d %d %d %d %d %d %d %h %h %d %d %h %h %h\n",
    frame,tick,scan,dot_in,low_bg,high_bg,low_obj,high_obj,obj_ok,extra,attr,oattr,ox,read_ok,valid_ok,logical_in,physical_in,byte_value);
   if(dummy==18)begin
    if(last_tick>=0)begin
     if(tick<=last_tick)$fatal(1,"nonmonotonic replay");
     repeat(tick-last_tick-1)@(negedge clk);
    end
    scanline=scan;dot=dot_in;bg_low=low_bg;bg_high=high_bg;obj_low=low_obj;obj_high=high_obj;obj_valid=obj_ok;
    extra_sprites=extra;bg_attribute=attr;obj_attribute=oattr;obj_x=ox;
    ppu_read=read_ok;ppu_valid=valid_ok;logical_address=logical_in;physical_address=physical_in;ppu_ce=1;
    #1; // Allow combinational address/descriptor predicates to settle.
    // Corrupt the actual formerly rejected high edge, one cause at a time.
    if(mode!=0 && !injected && high_bg && dut.pair_pending && !baseline.pair_ok)begin
     injected=1;
     case(mode)
      1:ppu_valid=0;
      2:physical_address=physical_address^22'h10;
      3:logical_address=logical_address^14'h10;
      4:bg_attribute=bg_attribute^2'b01;
      5:logical_address[3]=0;
      6:rom_fault=1;
     endcase
    end
    @(negedge clk);ppu_ce=0;rom_fault=0;last_tick=tick;
   end
  end
  wait(owned && old_owned && compact_owned);@(negedge clk);
  if(mode && !injected)$fatal(1,"negative cause was not exercised");
  $fwrite(output_file,"H %0d %02h %0d %0d %0d %0d\n",compact_valid,compact_errors,row_count,group_count,object_count,exception_count);
  $display("FETCH new=%0d/%02h old=%0d/%02h",valid,errors,old_valid,old_errors);
  if(mode==0 && (!valid || !compact_valid))$fatal(1,"positive pair or producer rejected");
  if(mode!=0 && (valid || compact_valid))$fatal(1,"corrupted pair accepted");
  if(valid)begin
   for(index=0;index<8192;index=index+1)begin
    query=1;query_tile=index;@(negedge clk);
    if(!response || required_kind!==expected_set[index])$fatal(1,"required physical tile mismatch");
   end
   query=0;
   for(index=0;index<group_count*33;index=index+1)read_item(0,index,1);
   for(index=0;index<row_count;index=index+1)read_item(1,index,1);
   for(index=0;index<object_count;index=index+1)read_item(2,index,1);
   for(index=0;index<exception_count;index=index+1)read_item(3,index,1);
   read_item(0,group_count*33,0);read_item(1,row_count,0);read_item(2,object_count,0);read_item(3,exception_count,0);
  end else read_item(0,0,0);
  release_scene=1;@(negedge clk);release_scene=0;query=1;compact_query=1;
  @(negedge clk);if(response || compact_response || owned || compact_owned || valid || compact_valid)$fatal(1,"stale release lease");
  $fclose(input_file);$fclose(output_file);$fclose(event_file);$fclose(old_file);
  $display("PASS PLANES165 mode=%0d",mode);$finish;
 end
 initial begin #30000000;$fatal(1,"pair replay watchdog");end
endmodule
