// SPDX-License-Identifier: MIT
// Bounded SNES boot milestones. Host-domain snapshots; no live multibit CDC.
// Writes00:7000=stage,7001=error. SPI73: D9,stage,error,flags,frames16,version1.
// Flags: bit0 reset-vector-low read,bit1 high read,bit2 any program read.
// A milestone records software progress, not proof of physical TV pixels.
module nes_screen_status142(
 input wire clk,reset,active,
 input wire [23:0] address,input wire read_n,write_n,romsel_n,
 input wire [7:0] data_in,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,
 output wire receive_write,selected,miso
);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [1:0] wr_sync,rd_sync,ss_sync,sck_sync,mosi_sync,active_sync;
 reg [23:0] addr_meta,addr_sync,addr_previous;
 reg [7:0] data_meta,data_sync,data_previous;
 reg wr_previous,rd_previous,seen,sck_previous;
 reg [7:0] stage,error_code;
 reg [2:0] flags;
 reg [15:0] frames;
 reg [2:0] bit_count;reg [3:0] byte_count;
 reg [7:0] shift,command;reg [55:0] snapshot;
 reg miso_hold;reg [7:0] reply;
 wire milestone=address==24'h007000 || address==24'h007001;
 assign receive_write=!reset&&active&&read_n&&!write_n&&milestone;
 wire qualified=!wr_sync[1]&&!wr_previous&&rd_sync[1]&&rd_previous&&
                 addr_sync==addr_previous&&data_sync==data_previous;
 wire [7:0] incoming={shift[6:0],mosi_sync[1]};
 assign selected=!reset&&!SPI_SS&&command==8'h73&&byte_count!=0;
 assign miso=miso_hold;
 always @* begin
  case(byte_count)
   1:reply=snapshot[55:48];2:reply=snapshot[47:40];3:reply=snapshot[39:32];
   4:reply=snapshot[31:24];5:reply=snapshot[23:16];6:reply=snapshot[15:8];
   7:reply=snapshot[7:0];default:reply=0;
  endcase
 end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   wr_sync<=3;rd_sync<=3;active_sync<=0;wr_previous<=1;rd_previous<=1;seen<=0;
   addr_meta<=0;addr_sync<=0;addr_previous<=0;
   data_meta<=0;data_sync<=0;data_previous<=0;
   stage<=0;error_code<=0;flags<=0;frames<=0;
   ss_sync<=3;sck_sync<=0;mosi_sync<=0;sck_previous<=0;
   bit_count<=0;byte_count<=0;shift<=0;command<=0;snapshot<=0;miso_hold<=0;
  end else begin
   wr_sync<={wr_sync[0],write_n};rd_sync<={rd_sync[0],read_n};active_sync<={active_sync[0],active};
   wr_previous<=wr_sync[1];rd_previous<=rd_sync[1];
   addr_meta<=address;addr_sync<=addr_meta;addr_previous<=addr_sync;
   data_meta<=data_in;data_sync<=data_meta;data_previous<=data_sync;
   if(wr_sync[1])seen<=0;
   if(active_sync[1]&&qualified&&!seen)begin
    seen<=1;
    if(addr_sync==24'h007000)begin
     stage<=data_sync;
     if(data_sync==8'd6 && frames!=16'hffff)frames<=frames+1'b1;
    end
    if(addr_sync==24'h007001 && error_code==0)error_code<=data_sync;
   end
   // Diagnostic activity flags only. Raw pins do not drive control decisions.
   if(active_sync[1]&&!read_n&&write_n&&!romsel_n&&addr_sync==address&&addr_previous==address)begin
    if(address==24'h00fffc)flags[0]<=1;
    if(address==24'h00fffd)flags[1]<=1;
    if(!address[22]&&address[15])flags[2]<=1;
   end
   ss_sync<={ss_sync[0],SPI_SS};sck_sync<={sck_sync[0],SPI_SCK};mosi_sync<={mosi_sync[0],SPI_MOSI};
   sck_previous<=sck_sync[1];
   if(ss_sync[1])begin bit_count<=0;byte_count<=0;command<=0;miso_hold<=0;end
   else begin
    if(!sck_sync[1]&&sck_previous)miso_hold<=reply[7-bit_count];
    if(sck_sync[1]&&!sck_previous)begin
     shift<=incoming;bit_count<=bit_count+1'b1;
     if(bit_count==7)begin
      if(byte_count!=9)byte_count<=byte_count+1'b1;
      if(byte_count==0)begin command<=incoming;snapshot<={8'hd9,stage,error_code,5'd0,flags,frames,8'd1};end
     end
    end
   end
  end
 end
endmodule
