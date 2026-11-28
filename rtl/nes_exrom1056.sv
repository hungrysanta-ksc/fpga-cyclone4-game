// SPDX-License-Identifier: MIT
// CHR-RAM ExROM profile. The DQ4 cartridge uses CPU ExRAM mode 2,
// 16 KiB PRG pairs and CIRAM pages 0/1. This is not a general MMC5 PPU.
module nes_exrom1056(
 input wire clk,reset,ce,wr,
 input wire [15:0] cpu,input wire [7:0] data,input wire [13:0] ppu,
 output wire [19:0] prg,output wire ram_selected,ram_writable,
 output wire nt_page,output wire [7:0] mapper_data
);
 reg [1:0] mode,protect1,protect2,ex_mode;
 reg [7:0] nt_map,bank4,bank5,bank6,bank7;
 reg [7:0] selected;
 always @* case(mode)
   0:selected={bank7[7:2],cpu[14:13]};
   1:selected=cpu[14] ? {bank7[7:1],cpu[13]} : {bank5[7:1],cpu[13]};
   2:selected=cpu[14] ? (cpu[13] ? bank7 : bank6) : {bank5[7:1],cpu[13]};
   3:case(cpu[14:13])
       0:selected=bank4;
       1:selected=bank5;
       2:selected=bank6;
       3:selected=bank7;
     endcase
 endcase
 wire forced_rom=cpu[14:13]==3 || mode==0 || (mode==1 && cpu[14]);
 assign ram_selected=cpu[15:13]==3'b011 || (cpu[15] && !forced_rom && !selected[7]);
 assign ram_writable=protect1==2 && protect2==1;
 assign prg={selected[6:0],cpu[12:0]};
 assign nt_page=nt_map[{ppu[11:10],1'b0}];
 wire ex=cpu[15:10]==6'h17;
 (* ramstyle="M9K" *) reg [7:0] exram[0:1023];
 reg [7:0] ex_data;
 always @(posedge clk) begin
   ex_data<=exram[cpu[9:0]];
   if(!reset && ce && wr && ex && ex_mode==2)exram[cpu[9:0]]<=data;
 end
 assign mapper_data=(ex && ex_mode[1]) ? ex_data : (cpu==16'h5204 ? 8'd0 : cpu[15:8]);
 always @(posedge clk)begin
   if(reset)begin mode<=3;bank4<=0;bank5<=0;bank6<=0;bank7<=255;
     nt_map<=0;protect1<=0;protect2<=0;ex_mode<=0;
   end else if(ce && wr) case(cpu)
     16'h5100:mode<=data[1:0];
     16'h5102:protect1<=data[1:0];
     16'h5103:protect2<=data[1:0];
     16'h5104:ex_mode<=data[1:0];
     16'h5105:nt_map<=data;
     16'h5114:bank4<=data;
     16'h5115:bank5<=data;
     16'h5116:bank6<=data;
     16'h5117:bank7<=data;
   endcase
 end
endmodule
