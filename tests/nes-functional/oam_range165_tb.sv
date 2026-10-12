// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module oam_range165_tb;
reg clk=0; always #5 clk=~clk;
reg ce=0,reset=1,clear_signal=0,end_of_line=0,rendering_enabled=0,obj_size=1;
reg [8:0] scanline=12,cycle=66;
reg oam_addr_write=0,oam_data_write=0;reg [7:0] oam_din=0;
reg is_vbe=0,PAL=0,is_pre_render=0;
reg [63:0] SaveStateBus_Din=0;reg [9:0] SaveStateBus_Adr=12;
reg SaveStateBus_wren=0,SaveStateBus_rst=1;
reg [7:0] Savestate_OAMAddr=0,Savestate_OAMWriteData=0,native_oam_address=0;
reg Savestate_OAMRdEn=0,Savestate_OAMWrEn=0;
oam_reference reference(.oam_bus(),.oam_bus_ex(),.overflow(),.sprite0(),.in_range(),.masked_sprites(),.SaveStateBus_Dout(),.Savestate_OAMReadData(),.native_oam_data(),.native_oam_write(),.*);
oam_banked candidate(.oam_bus(),.oam_bus_ex(),.overflow(),.sprite0(),.in_range(),.masked_sprites(),.SaveStateBus_Dout(),.Savestate_OAMReadData(),.native_oam_data(),.native_oam_write(),.*);
integer accepted=0,rejected=0;
initial begin
 repeat(3)@(negedge clk);SaveStateBus_rst=0;
 // Distinct bytes make a wrong bank or byte index observable.
 for(integer a=0;a<256;a++)begin
  Savestate_OAMAddr=a;Savestate_OAMWriteData=(a%4==0)?8'd5:(a^8'h96);
  Savestate_OAMWrEn=1;@(negedge clk);
 end
 Savestate_OAMWrEn=0;
 for(integer row=0;row<16;row++)begin
  reset=1;ce=0;@(negedge clk);
  reset=0;ce=1;rendering_enabled=1;
  reference.old_rendering=1;candidate.old_rendering=1;
  reference.oam_secondary_row_ex=row;candidate.oam_secondary_row_ex=row;
  reference.oam_addr_ex=3;candidate.oam_addr_ex=3;
  reference.spr_counter=7;candidate.spr_counter=7;
  reference.ex_ovr=0;candidate.ex_ovr=0;
  reference.eval_count=0;candidate.eval_count=0;
  @(negedge clk);
  for(integer a=0;a<64;a++)begin
   if(reference.oam_temp[a]!==candidate.oam_temp[a])$fatal(1,"range mismatch row=%0d byte=%0d",row,a);
   if(row<8 && a>=32+row*4 && a<36+row*4)begin
    if(candidate.oam_temp[a]!==reference.oam_read(12+a%4))$fatal(1,"missing upper write");
   end else if(candidate.oam_temp[a]!==8'hff)$fatal(1,"unowned byte changed row=%0d byte=%0d",row,a);
  end
  if(row<8)accepted++;else rejected++;
 end
 if(accepted!=8 || rejected!=8)$fatal(1,"coverage");
 $display("PASS OAM RANGE accepted=%0d rejected=%0d bytes=1024",accepted,rejected);$finish;
end
initial begin #100000;$fatal(1,"watchdog");end
endmodule
