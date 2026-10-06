// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module oam_banked_tb;
 reg clk=0;always #5 clk=~clk;
 reg ce=0,reset=1,clear_signal=0,end_of_line=0,rendering_enabled=0,obj_size=0;
 reg [8:0] scanline=0,cycle=0;reg oam_addr_write=0,oam_data_write=0;reg [7:0] oam_din=0;
 reg is_vbe=0,PAL=0,is_pre_render=0;
 reg [63:0] SaveStateBus_Din=0;reg [9:0] SaveStateBus_Adr=12;
 reg SaveStateBus_wren=0,SaveStateBus_rst=1;
 reg [7:0] Savestate_OAMAddr=0,Savestate_OAMWriteData=0;
 reg Savestate_OAMRdEn=0,Savestate_OAMWrEn=0;
 wire [7:0] ref_bus,new_bus,ref_read,new_read;wire [31:0] ref_ex,new_ex;
 wire ref_over,new_over,ref_s0,new_s0,ref_range,new_range,ref_mask,new_mask;
 wire [63:0] ref_ss,new_ss;
 oam_reference reference(.oam_bus(ref_bus),.oam_bus_ex(ref_ex),.overflow(ref_over),.sprite0(ref_s0),.in_range(ref_range),.masked_sprites(ref_mask),.SaveStateBus_Dout(ref_ss),.Savestate_OAMReadData(ref_read),.*);
 oam_banked candidate(.oam_bus(new_bus),.oam_bus_ex(new_ex),.overflow(new_over),.sprite0(new_s0),.in_range(new_range),.masked_sprites(new_mask),.SaveStateBus_Dout(new_ss),.Savestate_OAMReadData(new_read),.*);
 integer cycles_checked=0,row_copies=0,cpu_writes=0,ss_writes=0,collisions=0;
 reg checking=0;reg [31:0] rng=32'h480ab19f;
 function automatic [31:0] next_rng(input [31:0] x);reg [31:0] v;begin v=x^(x<<13);v=v^(v>>17);next_rng=v^(v<<5);end endfunction
 always @(posedge clk)if(checking)begin
  if(!reset && ce && !reference.old_rendering && reference.rendering && !PAL && reference.old_using_secondary!=reference.using_secondary)begin row_copies++;if(Savestate_OAMWrEn)collisions++;end
  if(!reset && ce && oam_data_write && !reference.rendering)begin cpu_writes++;if(Savestate_OAMWrEn)collisions++;end
  if(Savestate_OAMWrEn)ss_writes++;
  #1;
  if({ref_bus,ref_ex,ref_over,ref_s0,ref_range,ref_mask,ref_ss,ref_read}!=={new_bus,new_ex,new_over,new_s0,new_range,new_mask,new_ss,new_read})$fatal(1,"output mismatch at%0d",cycles_checked);
  if(reference.SS_OAMEVAL_BACK!==candidate.SS_OAMEVAL_BACK ||
     {reference.eval_count,reference.last_y,reference.last_tile,reference.last_attr}!=={candidate.eval_count,candidate.last_y,candidate.last_tile,candidate.last_attr})$fatal(1,"state mismatch%0d",cycles_checked);
  for(integer i=0;i<256;i++)if(reference.oam[i]!==candidate.oam_read(i))$fatal(1,"primary OAM mismatch cycle%0d addr%0d ref%h new%h",cycles_checked,i,reference.oam[i],candidate.oam_read(i));
  for(integer i=0;i<64;i++)if(reference.oam_temp[i]!==candidate.oam_temp[i])$fatal(1,"secondary OAM mismatch%0d addr%0d",cycles_checked,i);
  cycles_checked++;
 end
 initial begin
  repeat(3)@(negedge clk);SaveStateBus_rst=0;checking=1;
  // Initialize only through the existing savestate write port; no rewritten RAM pokes.
  for(integer i=0;i<256;i++)begin Savestate_OAMWrEn=1;Savestate_OAMAddr=i;Savestate_OAMWriteData=(i*37)^8'ha6;@(negedge clk);end
  Savestate_OAMWrEn=0;reset=0;
  // Same-address CPU/savestate collisions: CPU write wins in the original order.
  ce=1;rendering_enabled=0;oam_addr_write=1;oam_data_write=1;Savestate_OAMWrEn=1;
  for(integer i=0;i<256;i++)begin
   oam_din=i;Savestate_OAMAddr=i;Savestate_OAMWriteData=~i;
   @(negedge clk);
   if(reference.oam[i]!==((i%4==2)?(i&8'he3):i[7:0]))$fatal(1,"CPU/SS priority");
  end
  oam_addr_write=0;oam_data_write=0;Savestate_OAMWrEn=0;
  // Rendering-rise copy collides with one savestate byte in each destination lane.
  for(integer lane=0;lane<8;lane++)begin
   reset=1;ce=0;rendering_enabled=0;@(negedge clk);
   reset=0;ce=1;cycle=64;scanline=0;rendering_enabled=1;PAL=0;
   Savestate_OAMWrEn=1;Savestate_OAMAddr=lane;Savestate_OAMWriteData=8'h5a;
   @(negedge clk);Savestate_OAMWrEn=0;rendering_enabled=0;
  end
  // First preserve upstream X state; then equal directed seeds cover evaluator states.
  repeat(100)begin ce=1;cycle=cycle+1'b1;@(negedge clk);end
  for(integer seed=0;seed<4;seed++)begin
   reference.eval_count=seed;candidate.eval_count=seed;
   for(integer i=0;i<5000;i++)begin
    rng=next_rng(rng);ce=rng[0];reset=(i%257)==0;PAL=rng[1];rendering_enabled=rng[2];
    scanline=rng[10:2]%312;cycle=rng[19:11]%341;is_pre_render=scanline==261;clear_signal=is_pre_render;end_of_line=cycle==340;obj_size=rng[3];is_vbe=scanline==260;
    oam_addr_write=rng[4];oam_data_write=rng[5];oam_din=rng[23:16];
    Savestate_OAMWrEn=rng[6];Savestate_OAMRdEn=rng[7];Savestate_OAMAddr=rng[31:24];Savestate_OAMWriteData=rng[15:8];
    @(negedge clk);
   end
  end
  reset=0;oam_addr_write=0;oam_data_write=0;Savestate_OAMWrEn=0;Savestate_OAMRdEn=1;ce=1;
  reference.eval_count=0;candidate.eval_count=0;
  // Complete NTSC and PAL scanline cadence; rendering toggles exercise row corruption.
  for(integer region=0;region<2;region++)begin
   PAL=region;
   for(integer line=0;line<(region?312:262);line++)begin
    scanline=line;is_pre_render=line==(region?311:261);clear_signal=is_pre_render;is_vbe=line==(region?310:260);obj_size=line[0];
    for(integer dot=0;dot<341;dot++)begin
     cycle=dot;end_of_line=dot==340;rendering_enabled=(dot%29)!=0;Savestate_OAMAddr=dot;
     @(negedge clk);
    end
   end
  end
  $display("PASS OAM BANKING cycles=%0d row_copies=%0d cpu_writes=%0d ss_writes=%0d collisions=%0d",cycles_checked,row_copies,cpu_writes,ss_writes,collisions);$finish;
 end
 initial begin #10000000;$fatal(1,"watchdog");end
endmodule
