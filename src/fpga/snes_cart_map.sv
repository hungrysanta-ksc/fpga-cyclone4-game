// Candidate GBC frontend address map, independent of the legacy SGB mapper.
// SRAM: output pages 00000..0ffff; frontend 10000..4ffff.
// 50000..51fff is reserved for GBC save RAM (not exposed or implemented here).
module snes_cart_map(
 input wire[23:0]addr,input wire romsel_n,page,
 output wire reg_select,frame_select,program_select,
 output wire[18:0]sram_addr
);
 assign reg_select=!addr[22]&&addr[15:4]==12'h600;
 assign frame_select=!romsel_n&&addr[22:16]==7'h40&&addr[15];
 assign program_select=!romsel_n&&addr[22:19]==0&&addr[15];
 assign sram_addr=frame_select?{3'b000,page,addr[14:0]}:
                  program_select?(19'h10000+{1'b0,addr[18:16],addr[14:0]}):19'b0;
endmodule
