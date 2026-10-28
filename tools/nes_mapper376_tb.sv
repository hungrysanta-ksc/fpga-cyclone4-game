// SPDX-License-Identifier: MIT
// Boundary tests on selected375 collectors/plan decoder. Mapper addresses are
// resolved stimuli,not an implementation or validation of MMC4/MMC5 hardware.
`timescale 1ns/1ps
module mapper376_tb;
 parameter CASE=0;
 reg clk=0;always #22.727 clk=~clk;
 reg hclk=0;always #5.952 hclk=~hclk;
 reg reset=1;
 task tick;begin @(negedge clk);end endtask
 generate if(CASE<2)begin:planes
  reg pce=0,blo=0,bhi=0;reg [8:0] line=7,dot=257;
  reg [13:0] logical=0;reg [21:0] physical=0;
  wire initialized,active,owned,valid,ev,response;wire [7:0] errors;
  wire [15:0] generation;wire [63:0] data;wire [1:0] required;
  integer events=0;reg [12:0] tags[0:3];
  nes_native_planes165 #(.REQUIRED_BITMAP(0)) dut(.clk(clk),.reset(reset),.release_scene(1'b0),.ppu_ce(pce),.rom_fault(1'b0),
   .scanline(line),.dot(dot),.bg_low(blo),.bg_high(bhi),.obj_low(1'b0),.obj_high(1'b0),.obj_valid(1'b0),.extra_sprites(1'b0),
   .bg_attribute(2'd2),.obj_attribute(8'd0),.obj_x(8'd0),.ppu_read(1'b1),.ppu_valid(1'b1),.logical_address(logical),.physical_address(physical),
   .query(1'b0),.query_tile(13'd0),.initialized(initialized),.active(active),.owned(owned),.valid(valid),.errors(errors),.generation(generation),
   .event_valid(ev),.event_data(data),.response(response),.required_kind(required));
  always @(negedge clk)if(ev)begin tags[events]=data[12:0];events++;end
  task pair(input [13:0] a,input [21:0] resolved);
   begin line=8;dot=5;logical=a;physical=resolved;blo=1;pce=1;tick();blo=0;pce=0;repeat(3)tick();
    logical=a^14'd8;physical=resolved^22'd8;bhi=1;pce=1;tick();bhi=0;pce=0;repeat(4)tick();end
  endtask
  initial begin
   repeat(4)tick();reset=0;tick();pce=1;tick();pce=0;repeat(3)tick();
   if(!active)$fatal(1,"collector did not begin376");
   if(CASE==0)begin
    // A trigger pair must retain its resolved old bank;the next fetch may
    // use a different bank at the same logical tile. No preview mapper read.
    pair(14'h0fd0,22'h201fd0);pair(14'h0120,22'h205120);pair(14'h0120,22'h201120);
   end else pair(14'h0120,22'h220120); // First byte beyond current128KiB CHR.
   line=232;dot=1;pce=1;tick();pce=0;repeat(6)tick();
   if(!owned)$fatal(1,"collector not sealed376");
   if(CASE==0)begin
    if(!valid||errors||events!=3||tags[0]!=13'h1fd||tags[1]!=13'h512||tags[2]!=13'h112)$fatal(1,"resolved bank history lost376");
   end else if(valid||events||!errors[1]||!errors[2])$fatal(1,"high CHR address aliased/accepted376");
   $display("PASS MAPPER376 case=%0d events=%0d valid=%0d errors=%02x",CASE,events,valid,errors);$finish;
  end
 end else if(CASE<4)begin:compact
  reg begin_scene=0,end_scene=0,ev=0,commit=0,query=0;reg [63:0] event_data=0;
  reg [7:0] committed_row=0;reg [10:0] query_address=0;
  wire patch,active,owned,valid,response,hit;wire [7:0] errors,rows,objects,exceptions;wire [5:0] groups;wire [63:0] data;
  nes_native_compact181 dut(.clk(clk),.reset(reset),.release_scene(1'b0),.begin_scene(begin_scene),.end_scene(end_scene),.source_fault(1'b0),
   .event_valid(ev),.event_data(event_data),.row_commit(commit),.row_patched(1'b0),.committed_row(committed_row),.row_needs_patch(patch),
   .query(query),.query_kind(2'd0),.query_address(query_address),.active(active),.owned(owned),.valid(valid),.errors(errors),
   .row_count(rows),.object_count(objects),.exception_count(exceptions),.group_count(groups),.response(response),.hit(hit),.data(data));
  integer fine;
  initial begin
   repeat(4)tick();reset=0;begin_scene=1;tick();begin_scene=0;repeat(3)tick();
   for(integer row=0;row<224;row++)begin
    for(integer col=0;col<33;col++)begin
     // Per8pixel palette fits the15bit cell. A non-aligned split's different
     // fineY consumes one bounded exception per affected cell on every row.
     fine=(row%8+((CASE==3&&col>=16)?3:0))%8;
     event_data=0;event_data[12:0]=100+col;event_data[15:13]=fine;
     event_data[32:25]=row;event_data[40:33]=col;event_data[48:41]=col%4;
     ev=1;tick();ev=0;repeat(3)tick();
    end
    committed_row=row;commit=1;tick();commit=0;repeat(36)tick();
   end
   end_scene=1;tick();end_scene=0;repeat(6)tick();
   if(!owned||rows!=224)$fatal(1,"compact frame incomplete376");
   if(CASE==2)begin
    if(!valid||errors||exceptions||groups!=28)$fatal(1,"per-cell palette rejected376");
    for(integer col=0;col<33;col++)begin
     query_address=col;query=1;tick();
     if(!response||!hit||data[14:13]!=col%4||data[12:0]!=100+col)$fatal(1,"per-cell palette/tag query mismatch376");
     query=0;repeat(2)tick();
    end
   end else if(valid||!errors[2]||exceptions!=128)$fatal(1,"split exception capacity not enforced376");
   $display("PASS MAPPER376 case=%0d rows=%0d groups=%0d exceptions=%0d valid=%0d errors=%02x",CASE,rows,groups,exceptions,valid,errors);$finish;
  end
 end else begin:plan
  reg write_valid=0,seal=0;reg [7:0] write_data=0;reg [15:0] crc=16'hffff;
  wire write_ready,valid,fault,ready,retired,retire_commit,pzero,pstep,end_valid,end_partial;wire [9:0] cursor,slot;wire [1:0] kind;
  wire [15:0] generation,end_generation;wire [12:0] tag;wire [7:0] mask,altmask;wire [47:0] rows;wire [103:0] alt;
  nes_plan_batch206 dut(.host_clk(hclk),.nes_clk(clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(1'b0),
   .plan_cursor319(cursor),.plan_zero319(pzero),.plan_step319(pstep),.write_valid(write_valid),.write_ready(write_ready),.write_data(write_data),
   .retire(1'b0),.retire_done(retired),.retire_permitted(1'b0),.retire_commit(retire_commit),.seal(seal),.seal_length(10'd7),.seal_plans(5'd1),.seal_crc(crc),
   .host_idle(ready),.fault(fault),.lease_valid(1'b1),.lease_generation(16'd1),.plan_valid(valid),.plan_ready(1'b0),.tile_done(1'b0),
   .plan_kind(kind),.plan_generation(generation),.plan_slot(slot),.plan_tag(tag),.plan_mask(mask),.plan_rows(rows),.plan_alt_mask(altmask),.plan_alt_tags(alt),
   .end_valid(end_valid),.end_ready(1'b0),.end_generation(end_generation),.end_partial295(end_partial));
  function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
   reg [15:0] c;begin c=c0^{b,8'd0};for(integer i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
  endfunction
  task put(input [7:0] b);
   begin wait(write_ready);@(negedge hclk);write_valid=1;write_data=b;crc=c16(crc,b);@(negedge hclk);write_valid=0;end
  endtask
  initial begin
   repeat(5)tick();reset=0;repeat(8)tick();
   put(128);put(1);put(0);put(1);put(0);put(CASE==4?255:0);put(CASE==4?31:32);
   @(negedge hclk);seal=1;@(negedge hclk);seal=0;
   wait(valid||fault);repeat(4)tick();
   if(CASE==4)begin if(fault||!valid||tag!=8191)$fatal(1,"13bit boundary rejected376");end
   else if(!fault||valid)$fatal(1,"16bit MMC5 tag aliased/accepted376");
   $display("PASS MAPPER376 case=%0d valid=%0d fault=%0d",CASE,valid,fault);$finish;
  end
 end endgenerate
 initial begin #5000000;$fatal(1,"mapper376 timeout case%0d",CASE);end
endmodule
