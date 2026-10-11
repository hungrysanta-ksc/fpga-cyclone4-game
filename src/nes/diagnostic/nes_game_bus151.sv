// SPDX-License-Identifier: MIT
// Game client ROM + address-based framebuffer reads, including continuous DMA.
module nes_game_bus151(
 input wire host_clk,reset,active,
 input wire [23:0] address,input wire read_n,write_n,romsel_n,
 input wire [7:0] data_in,output wire [7:0] data_out,output wire oe_n,dir,
 input wire frame_ready,input wire frame_response,input wire [7:0] frame_data,
 output reg frame_request,output reg [15:0] frame_address,output reg release_frame,
 output reg pad_commit,output reg [15:0] pad_buttons
);
 // Asynchronous assertion, local host-clock release. NES reset is already
 // released by core_release in its own domain at the physical top.
 (* async_reg="true" *) reg [1:0] host_release;
 always @(posedge host_clk or posedge reset)
  if(reset)host_release<=0;else host_release<={host_release[0],1'b1};
 wire host_reset=!host_release[1];

 (* ramstyle="M9K" *) reg [7:0] program_rom[0:2047];
 initial $readmemh("game-program.hex",program_rom);
 reg [7:0] rom_data;
 reg [23:0] address_meta,address_sync,rom_tag,result_tag,pending_tag;
 reg read_meta,read_sync,write_meta,write_sync,written,pending,result_valid;
 reg [7:0] result_data;
 reg [7:0] data_meta,data_sync,data_previous;
 reg [23:0] address_previous;reg read_previous,write_previous;
 wire stable_address=address_meta==address_sync;
 wire local_bank=address[23:16]==0;
 wire local_control=local_bank && (address[15:0]==16'h6000 || address[15:0]==16'h6002 || address[15:0]==16'h6003);
 wire rom_read=local_bank && address[15] && !romsel_n;
 wire frame_read=address[23:16]==8'h40;
 wire active_read=active && !reset && !read_n && write_n;
 wire control_write=active && !reset && read_n && !write_n && local_control;
 assign dir=active_read && (rom_read || frame_read || local_control);
 assign oe_n=!(control_write || (dir &&
   ((rom_read && rom_tag==address) || local_control ||
    (frame_read && frame_ready && result_valid && result_tag==address))));
 assign data_out=rom_read?rom_data:local_control?{7'd0,frame_ready}:result_data;
 always @(posedge host_clk)begin
  rom_data<=program_rom[address_sync[10:0]];rom_tag<=address_sync;
 end
 always @(posedge host_clk or posedge host_reset)begin
  if(host_reset)begin
   address_meta<=0;address_sync<=0;read_meta<=1;read_sync<=1;write_meta<=1;write_sync<=1;
   data_meta<=0;data_sync<=0;data_previous<=0;address_previous<=0;read_previous<=1;write_previous<=1;
   frame_request<=0;frame_address<=0;release_frame<=0;pad_commit<=0;pad_buttons<=0;
   written<=0;pending<=0;result_valid<=0;result_tag<=0;pending_tag<=0;result_data<=0;
  end else begin
   address_meta<=address;address_sync<=address_meta;address_previous<=address_sync;
   data_meta<=data_in;data_sync<=data_meta;data_previous<=data_sync;
   read_previous<=read_sync;write_previous<=write_sync;
   read_meta<=read_n;read_sync<=read_meta;write_meta<=write_n;write_sync<=write_meta;
   frame_request<=0;release_frame<=0;pad_commit<=0;
   if(write_sync)written<=0;
   // Commit once at the synchronized END of the write. The previous
   // tuple is the last host sample taken while raw /WR was low.
   // Early write data may still contain the preceding bus value.
   if(active && write_sync && !write_previous && read_previous)begin
    written<=1;
    if(address_previous==24'h006000 && data_previous==8'ha5)begin release_frame<=1;result_valid<=0;end
    if(address_previous==24'h006002)pad_buttons[7:0]<=data_previous;
    if(address_previous==24'h006003)begin pad_buttons[15:8]<=data_previous;pad_commit<=1;end
   end
   if(frame_response && pending)begin
    pending<=0;result_valid<=1;result_tag<=pending_tag;result_data<=frame_data;
   end
   if(!frame_ready)result_valid<=0;
   if(active && frame_ready && stable_address && !read_sync && write_sync &&
      address_sync[23:16]==8'h40 && !pending &&
      (!result_valid || result_tag!=address_sync))begin
    frame_address<={~address_sync[15],address_sync[14:0]};
    frame_request<=1;pending<=1;pending_tag<=address_sync;
   end
  end
 end
endmodule
