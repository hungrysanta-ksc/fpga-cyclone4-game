// SPDX-License-Identifier: MIT
// Actual fixed CHR-ROM loader lifetime: mem-clock BEGIN changes content epoch.
// Registered Gray ID crosses to NES; invalidation is asynchronous, admission
// waits for reset release and a stable synchronized ID. No reset on frame ACK.
module nes_source_epoch204(
 input wire mem_clk,nes_clk,reset,load_begin,load_valid,
 input wire loaded,run_enable,loader_fault,
 input wire [18:0] loaded_bytes,
 output wire source_ready,source_is_rom,source_writing,
 output wire [31:0] live_epoch
);
 reg [31:0] serial,gray;reg exhausted;
 wire [31:0] next_serial=serial+32'd1;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin serial<=0;gray<=0;exhausted<=0;end
  else if(load_begin)begin
   if(serial==32'hffffffff)exhausted<=1;
   else begin serial<=next_serial;gray<=next_serial^(next_serial>>1);end
  end
 end
 // This loader accepts exactly256KiB PRG+128KiB CHR-ROM, including its32KiB
 // mirror mode. A future CHR-RAM loader must change this admission contract.
 wire invalid=reset||exhausted||loader_fault||!loaded||!run_enable||
              loaded_bytes!=19'h60000||load_begin||load_valid;
 wire held;
 nes_domain_reset124 release_ready(.clk(nes_clk),.raw_reset(invalid),.reset(held));
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)
 reg [31:0] epoch_meta,epoch_sync;
 reg [31:0] previous;reg admitted;
 always @(posedge nes_clk or posedge reset)begin
  if(reset)begin epoch_meta<=0;epoch_sync<=0;previous<=0;end
  else begin epoch_meta<=gray;epoch_sync<=epoch_meta;previous<=epoch_sync;end
 end
 always @(posedge nes_clk or posedge held)begin
  if(held)admitted<=0;
  else admitted<=epoch_sync==previous;
 end
 assign source_ready=!invalid&&!held&&admitted;
 assign source_is_rom=source_ready;
 assign source_writing=invalid;
 assign live_epoch=epoch_sync; // Opaque ID: consumers compare, never increment.
endmodule
