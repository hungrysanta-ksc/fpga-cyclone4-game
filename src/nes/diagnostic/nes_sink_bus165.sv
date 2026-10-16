// SPDX-License-Identifier: MIT
// Replacement for151's framebuffer-facing bus, not a parallel bank40 owner.
// Raw read/reset gates cancel immediately; writes retire at synchronized /WR end.
module nes_sink_bus165 #(parameter PROGRAM_BYTES=4096)(
 input wire clk,reset,active,stop,fault,
 input wire [23:0] address,input wire read_n,write_n,romsel_n,input wire [7:0] data_in,
 output wire [7:0] data_out,output wire oe_n,dir,
 input wire packet_ready,input wire [8:0] packet_length,input wire [7:0] packet_data,
 output wire [7:0] packet_address,
 output reg ack_write,output reg [3:0] ack_index,output reg [7:0] ack_byte,output reg ack_publish,
 output reg pad_commit,output reg [15:0] pad_buttons
);
 // 194 may select8192; deployed users retain the exact4096 default.
 localparam ROM_BITS=$clog2(PROGRAM_BYTES);
 (* ramstyle="M9K" *) reg [7:0] program_rom[0:PROGRAM_BYTES-1];
 initial $readmemh("sink-program.hex",program_rom);
 reg [7:0] rom_data;reg [23:0] tag;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [23:0] address_meta,address_sync;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg read_meta,read_sync,write_meta,write_sync;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [7:0] data_meta,data_sync;
 reg [23:0] address_previous;reg [7:0] data_previous;reg read_previous,write_previous;
 wire local_bank=address[23:16]==0;
 wire control=local_bank&&(address[15:0]<=16'h6005&&address[15:0]>=16'h6000 || address[15:0]>=16'h6010&&address[15:0]<=16'h601c);
 wire rom_select=local_bank&&address[15]&&!romsel_n;
 wire stored=address[14:0]<(PROGRAM_BYTES-64)||address[14:0]>=15'h7fc0;
 wire packet_select=address[23:8]==16'h4000;
 wire read_active=active&&!reset&&!read_n&&write_n;
 wire packet_drive=packet_select&&packet_ready&&{1'b0,address[7:0]}<packet_length&&tag==address;
 wire write_active=active&&!reset&&read_n&&!write_n&&control;
 assign packet_address=address_sync[7:0];
 assign dir=read_active&&(control||rom_select||packet_select);
 assign oe_n=!(write_active||(dir&&(control||(rom_select&&tag==address)||packet_drive)));
 reg [7:0] control_data;
 always @*case(address[15:0])
  16'h6000:control_data={7'd0,packet_ready};
  16'h6001:control_data={(stop||fault),7'd0};
  16'h6004:control_data=packet_length[7:0];16'h6005:control_data={7'd0,packet_length[8]};
  default:control_data=0;
 endcase
 assign data_out=rom_select?(stored?rom_data:8'hff):control?control_data:packet_data;
 always @(posedge clk)begin rom_data<=program_rom[address_sync[ROM_BITS-1:0]];tag<=address_sync;end
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   address_meta<=0;address_sync<=0;address_previous<=0;data_meta<=0;data_sync<=0;data_previous<=0;
   read_meta<=1;read_sync<=1;read_previous<=1;write_meta<=1;write_sync<=1;write_previous<=1;
   ack_write<=0;ack_publish<=0;ack_index<=0;ack_byte<=0;pad_commit<=0;pad_buttons<=0;
  end else begin
   address_meta<=address;address_sync<=address_meta;address_previous<=address_sync;
   data_meta<=data_in;data_sync<=data_meta;data_previous<=data_sync;
   read_meta<=read_n;read_sync<=read_meta;read_previous<=read_sync;
   write_meta<=write_n;write_sync<=write_meta;write_previous<=write_sync;
   ack_write<=0;ack_publish<=0;pad_commit<=0;
   if(active&&write_sync&&!write_previous&&read_previous)begin
    if(address_previous==24'h006002)pad_buttons[7:0]<=data_previous;
    if(address_previous==24'h006003)begin pad_buttons[15:8]<=data_previous;pad_commit<=1;end
    if(address_previous>=24'h006010&&address_previous<=24'h00601b)begin
     ack_write<=1;ack_index<=address_previous[3:0];ack_byte<=data_previous;
    end
    if(address_previous==24'h00601c&&data_previous==8'ha5)ack_publish<=1;
   end
  end
 end
endmodule
