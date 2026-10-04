// Conditional slot scheduler. Only a NEW non-SRAM PHI2 cycle grants one write.
// Contract: next SRAM read strobe is >= 270 ns after this PHI2 rising edge.
// This bound requires hardware/CPU+DMA waveform validation before deployment.
// No grant is inferred from a stopped clock or a long idle level.
module snes_sram_slots(
 input wire clk,reset,phi2,input wire[23:0]addr,
 input wire read_n,write_n,romsel_n,page,snapshot_valid,upload_busy,writer_busy,
 output wire grant,foreground_read,output wire[18:0]foreground_addr,
 output reg protocol_error
);
 (* async_reg="true" *)reg[1:0]phi_sync;
 reg phi_previous;
 (* async_reg="true" *)reg[23:0]addr_meta,addr_sync;
 (* async_reg="true" *)reg[1:0]rd_sync,wr_sync,cs_sync;
 wire registers,frame,program_rom;
 snes_cart_map map(addr_sync,cs_sync[1],page,registers,frame,program_rom,foreground_addr);
 wire cycle_start=phi_sync[1]&&!phi_previous;
 wire permitted=program_rom||(frame&&snapshot_valid&&!upload_busy);
 assign foreground_read=!reset&&!rd_sync[1]&&wr_sync[1]&&permitted;
 assign grant=!reset&&!protocol_error&&cycle_start&&!frame&&!program_rom&&!writer_busy;
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   phi_sync<=0;phi_previous<=0;rd_sync<=3;wr_sync<=3;cs_sync<=3;
   addr_meta<=0;addr_sync<=0;protocol_error<=0;
  end else begin
   phi_sync<={phi_sync[0],phi2};phi_previous<=phi_sync[1];
   rd_sync<={rd_sync[0],read_n};wr_sync<={wr_sync[0],write_n};
   cs_sync<={cs_sync[0],romsel_n};addr_meta<=addr;addr_sync<=addr_meta;
   if((foreground_read&&writer_busy)||
      (!rd_sync[1]&&frame&&(!snapshot_valid||upload_busy)))protocol_error<=1;
  end
 end
endmodule
