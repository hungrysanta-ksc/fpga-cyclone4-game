// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module patch_ppu181_tb;
 reg clk=0,reset=1,ss_reset=1,ce=0,write=0;
 always #5 clk=~clk;
 reg [7:0] din=0;reg [2:0] ain=0;
 wire [1:0] sys_type=2'b00;
 wire [8:0] scanline,cycle;wire [5:0] color;wire [2:0] emphasis;
 wire [13:0] vram_addr;wire [7:0] mask;
 // Deterministic external pattern bytes, not a game/mapper/ROM service test.
 wire [7:0] vram_data=vram_addr[7:0]^vram_addr[13:6]^8'hb3;
 PPU ppu(.clk(clk),.cs(1'b0),.RWn(1'b1),.rst_behavior(1'b0),.ce(ce),.debug_dots(1'b0),
  .reset(reset),.cold_reset(reset),.sys_type(sys_type),.vs_ppu_type(4'd0),
  .color(color),.din(din),.ain(ain),.read(1'b0),.write(write),.vram_dbus_in(vram_data),
  .vram_addr(vram_addr),.scanline(scanline),.cycle(cycle),.emphasis(emphasis),
  .extra_sprites(1'b0),.mask(2'd0),.native_oam_address(8'd0),.native_display_mask(mask),
  .SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),
  .SaveStateBus_rst(ss_reset),.SaveStateBus_load(1'b0),
  .Savestate_OAMAddr(8'd0),.Savestate_OAMRdEn(1'b0),.Savestate_OAMWrEn(1'b0),.Savestate_OAMWriteData(8'd0));
 wire begin_frame=ce && scanline==7 && cycle==257;
 function automatic integer row_slot_of(input integer y);
  case(y)0:row_slot_of=0;1:row_slot_of=1;7:row_slot_of=2;8:row_slot_of=3;185:row_slot_of=4;186:row_slot_of=5;223:row_slot_of=6;default:row_slot_of=-1;endcase
 endfunction
 wire row_finish;
 wire need_patch=row_finish && row_slot_of(scanline-8)>=0;
 reg query=0;reg [2:0] query_slot=0;reg [7:0] query_x=0;
 wire owned,valid,response,hit;wire [5:0] data;wire [7:0] errors;wire [2:0] count;
 nes_patch_capture181 capture(.clk(clk),.reset(reset),.release_frame(1'b0),.begin_frame(begin_frame),
  .source_fault(1'b0),.ppu_ce(ce),.generation_in(16'd1),.scanline(scanline),.dot(cycle),.color(color),.emphasis(emphasis),
  .need_patch(need_patch),.query(query),.query_generation(16'd1),.query_slot(query_slot),.query_x(query_x),
  .active(),.owned(owned),.valid(valid),.generation(),.errors(errors),.count(count),.row_commit(),.row_patched(),
  .committed_row(),.row_slot(),.response(response),.hit(hit),.data(data),.row_finish(row_finish));
 reg [5:0] reference_pixels[0:1791];
 reg sampled_ce=0;integer total=0,observed=0,transitions=0,checked=0,blank_samples=0,resume_samples=0,fd;
 reg [5:0] prior_color=0;
 always @(posedge clk)sampled_ce<=ce && !reset;
 // Independent reference: the established post-CE falling-edge PPU observer.
 always @(negedge clk)begin
  if(sampled_ce && scanline>=8 && scanline<232 && cycle>=2 && cycle<=257)begin
   if($isunknown({color,emphasis}))$fatal(1,"unknown final PPU pixel");
   if(emphasis!=0)$fatal(1,"fixture unexpectedly emphasized");
   total++;
   if(scanline==193 && cycle>120 && cycle<152 && mask==0)blank_samples++;
   if(scanline==193 && cycle>160 && mask==8'h0a)resume_samples++;
   if(row_slot_of(scanline-8)>=0)begin
    reference_pixels[row_slot_of(scanline-8)*256+cycle-2]=color;observed++;
    if(color!=prior_color)transitions++;prior_color=color;
   end
  end
 end
 integer n=0,halt=0;
 initial begin
  repeat(5)@(negedge clk);ss_reset=0;
  repeat(5)@(negedge clk);reset=0;
  while(!owned)begin
   // Four master clocks per dot plus finite stalls; never freeze after CE.
   n++;ce=n%4==0 && halt==0;
   if(halt>0)halt--;
   else if(n%401==0 && !ce)halt=7;
   ain=1;din=8'h0a;write=ce && scanline==0 && cycle==100;
   // Actual PPUMASK writes switch rendering off/back on during selected rows.
   if(ce && scanline==193 && (cycle==120 || cycle==152))begin
    write=1;din=cycle==120?8'h00:8'h0a;
   end
   @(negedge clk);
  end
  ce=0;write=0;
  if(!valid || errors!=0 || count!=7 || total!=57344 || observed!=1792 || transitions<64 || blank_samples<20 || resume_samples<80)
   $fatal(1,"PPU capture valid%b err%h count%0d total%0d observed%0d transitions%0d mask%h",valid,errors,count,total,observed,transitions,mask);
  fd=$fopen("ppu-rows.txt","w");
  for(integer s=0;s<7;s++)for(integer x=0;x<256;x++)begin
   query=1;query_slot=s;query_x=x;
   @(posedge clk);#1;
   if(!response || !hit || data!==reference_pixels[s*256+x])$fatal(1,"PPU pixel mismatch slot%0d x%0d data%h expected%h",s,x,data,reference_pixels[s*256+x]);
   $fwrite(fd,"%0d %0d %02x\n",s,x,data);
   checked++;@(negedge clk);
  end
  $fclose(fd);
  $display("PASS PPU181 observed=%0d retained=%0d transitions=%0d blank=%0d resumed=%0d",total,checked,transitions,blank_samples,resume_samples);$finish;
 end
 initial begin #10000000;$fatal(1,"PPU watchdog");end
endmodule
