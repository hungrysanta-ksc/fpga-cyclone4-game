// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module ff3_oam1042_tb;
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
 reg [7:0] native_oam_address;
 wire [7:0] native_ref,native_new;wire wr_ref,wr_new;
 oam_reference reference(.native_oam_data(native_ref),.native_oam_write(wr_ref),.oam_bus(ref_bus),.oam_bus_ex(ref_ex),.overflow(ref_over),.sprite0(ref_s0),.in_range(ref_range),.masked_sprites(ref_mask),.SaveStateBus_Dout(ref_ss),.Savestate_OAMReadData(ref_read),.*);
 OAMEval candidate(.native_oam_data(native_new),.native_oam_write(wr_new),.oam_bus(new_bus),.oam_bus_ex(new_ex),.overflow(new_over),.sprite0(new_s0),.in_range(new_range),.masked_sprites(new_mask),.SaveStateBus_Dout(new_ss),.Savestate_OAMReadData(new_read),.*);

 int dots,copies,loads,repeats,collision_same,collision_distinct,shared_port_checks,extra_loads;
 bit [7:0] extra_read_rows;
 bit [31:0] rng=32'h4a617661;
 task automatic dot_step;
  #1;
  if(ce && !reset)begin
   if(reference.oam_temp[reference.oam_secondary_addr] !==
      (candidate.temp_valid[candidate.oam_secondary_addr]?candidate.secondary_q:8'hff) ||
      reference.temp_copy_data!==candidate.temp_copy_data)
      $fatal(1,"secondary read before dot %d",dots);
   if(reference.oam_copy_write)copies++;
   if(reference.temp_load)loads++;
   if(reference.temp_extra !== candidate.temp_extra ||
      (reference.temp_eval && !reference.ex_ovr &&
       reference.primary_extra[reference.oam_addr_ex[0]*32+:32] !== candidate.extra_sprite))
      $fatal(1,"extra sprite fetch mismatch dot %d, address %h",dots,reference.oam_addr_ex);
   if(reference.temp_extra)extra_loads++;
   if(rendering_enabled && cycle>=256 && cycle<320 && cycle[2:0]==0)
    extra_read_rows[reference.oam_secondary_addr[4:2]]=1;
   if(reference.temp_load && reference.oam_copy_write)begin
    if(reference.oam_secondary_addr==reference.oam_row_cur)collision_same++;
    else collision_distinct++;
   end
   if(rendering_enabled && cycle[0] && cycle>=64 && cycle<256 &&
      reference.eval_count==3 && !reference.oam_secondary_ovr)repeats++;
   if(oam_addr_write && reference.oam_addr[7:3]!=oam_din[7:3])shared_port_checks++;
  end
  @(posedge clk);#1;
  if({ref_bus,ref_ex,ref_ss,ref_over,ref_s0,ref_range,ref_mask,wr_ref} !==
     {new_bus,new_ex,new_ss,new_over,new_s0,new_range,new_mask,wr_new} ||
     (!Savestate_OAMRdEn && native_ref!==native_new) ||
     (Savestate_OAMRdEn && ref_read!==new_read))$fatal(1,"dot %d bus %h/%h extra %h/%h ss %h/%h native %h/%h read %h/%h",dots,ref_bus,new_bus,ref_ex,new_ex,ref_ss,new_ss,native_ref,native_new,ref_read,new_read);
  ce=0;
  repeat(3)@(posedge clk);#1;
  dots++;
 endtask
 // Drive addresses before the RAMs' sampling edge and compare at the next enable.
 task automatic apply_dot;
  @(negedge clk);dot_step();
 endtask
 // Exercise a restored mid-evaluation edge with both RAM ports writing.
 task automatic restored_pair(input bit same_row);
  ce=0;rendering_enabled=0;scanline=2;is_pre_render=0;PAL=0;cycle=67;
  oam_addr_write=0;oam_data_write=0;
  Savestate_OAMAddr=0;Savestate_OAMWriteData=2;Savestate_OAMWrEn=1;apply_dot();Savestate_OAMWrEn=0;
  SaveStateBus_Din=0;
  SaveStateBus_Din[25:23]=7;
  SaveStateBus_Din[60]=1;
  SaveStateBus_Din[55:48]=same_row?8'h18:8'h28;
  SaveStateBus_Din[13:9]=3;
  SaveStateBus_Din[8]=1;
  SaveStateBus_Din[7:0]=8'h66;
  SaveStateBus_wren=1;apply_dot();SaveStateBus_wren=0;
  reset=1;apply_dot();reset=0;rendering_enabled=1;ce=1;apply_dot();
  // Resume visible fetches with both implementations in the restored context.
  for(int i=0;i<2;i++)begin
   oam_addr_write=1;oam_din=i?8'h28:8'h18;cycle=256;ce=1;apply_dot();
  end
 endtask
 initial begin
  native_oam_address=0;repeat(4)@(posedge clk);#1;
  reset=0;SaveStateBus_rst=0;Savestate_OAMWrEn=1;
  for(int i=0;i<256;i++)begin
   Savestate_OAMAddr=i;Savestate_OAMWriteData=i*37+3;apply_dot();
  end
  Savestate_OAMWrEn=0;
  for(int i=0;i<256;i++)begin Savestate_OAMRdEn=1;Savestate_OAMAddr=i;apply_dot();end
  Savestate_OAMRdEn=0;
  for(int line=0;line<524;line++)begin
   scanline=line%262;is_pre_render=scanline==261;is_vbe=scanline==260;
   for(int x=0;x<341;x++)begin
    rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
    cycle=x;end_of_line=x==340;obj_size=line[0];PAL=line>=262;clear_signal=is_pre_render;
    ce=1;rendering_enabled=line<262 || rng[0];native_oam_address=rng[7:0];
    oam_addr_write=line>=262 && rng[2];oam_data_write=line>=262 && rng[3];oam_din=rng[23:16];
    if(x==64 && line%17==0)begin
     reference.eval_count=3;candidate.eval_count=3;
    end
    apply_dot();
   end
  end
  restored_pair(1);restored_pair(0);
  if(!copies || !loads || !repeats || !shared_port_checks || !collision_same || !collision_distinct || !extra_loads || extra_read_rows!=8'hff)$fatal(1,"incomplete port coverage copies=%0d loads=%0d repeat=%0d address=%0d same=%0d different=%0d high_writes=%0d high_rows=%h", copies,loads,repeats,shared_port_checks,collision_same,collision_distinct,extra_loads,extra_read_rows);
  $display("PASS FF3 OAM dots=%0d copies=%0d loads=%0d repeat=%0d same_row=%0d distinct_rows=%0d address_changes=%0d extra_loads=%0d extra_read_rows=%h",
           dots,copies,loads,repeats,collision_same,collision_distinct,shared_port_checks,extra_loads,extra_read_rows);$finish;
 end
endmodule
