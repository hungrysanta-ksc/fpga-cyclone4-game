// SPDX-License-Identifier: MIT
// Original053 diagnostic64KiB PRG +16/32KiB CHR byte-stream loader, memory clock.
// 067 diagnostic-only: one SETUP, three WRITE, one HOLD, one RELEASE clock.
// This file is materialized under the historical module name only by067.
// Fixed geometry only; no CRC, readback engine, MCU SPI decoder or save policy.
module nes_rom_loader(input wire mem_clk,reset,
 input wire load_begin,load_chr32,load_valid,load_end,start,stop,input wire [7:0] load_data,
 output wire load_ready,loaded,run_enable,output reg fault,output reg [3:0] error_code,
 output wire rom_chr32,
 output reg [16:0] loaded_bytes,
 output reg [21:0] load_address,output wire [15:0] load_pin_data,output wire load_drive,
 output wire load_1ce,load_2ce,load_oe,load_we,load_bhe,load_ble);
 localparam IDLE=0,RECEIVE=1,WRITE=2,HOLD=3,READY=4,RUN=5,FAILED=6,SETUP=7,RELEASE=8;
 reg [3:0] state;reg [1:0] remaining;reg chr32,chip,lane;reg [7:0] byte_hold;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] release_reset;
 always @(posedge mem_clk or posedge reset)if(reset)release_reset<=3;else release_reset<={release_reset[0],1'b0};
 wire active_reset=reset || release_reset[1];
 // Same accepted register drives length and core address mask.
 assign rom_chr32=chr32;
 wire [16:0] total=chr32?17'h18000:17'h14000;
 wire [21:0] byte_address=loaded_bytes[16]?22'h200000+{6'd0,loaded_bytes[15:0]}:{6'd0,loaded_bytes[15:0]};
 wire writing=!active_reset && (state==WRITE || state==HOLD);
 assign load_ready=!active_reset && !fault && state==RECEIVE && loaded_bytes<total;
 assign loaded=!active_reset && !fault && (state==READY || state==RUN);
 assign run_enable=!active_reset && !fault && state==RUN;
 wire driving=!active_reset && (state==SETUP || state==WRITE || state==HOLD);
 assign load_drive=driving;assign load_pin_data={byte_hold,byte_hold};
 assign load_1ce=!(writing && !chip);assign load_2ce=!(writing && chip);
 assign load_oe=1'b1;assign load_we=!(writing && state==WRITE);
 assign load_bhe=driving?lane:1'b1;assign load_ble=driving?!lane:1'b1;
 task automatic fail(input [3:0] code);begin fault<=1;error_code<=code;if(state!=WRITE && state!=HOLD)state<=FAILED;end endtask
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin state<=IDLE;remaining<=0;chr32<=0;chip<=0;lane<=0;byte_hold<=0;load_address<=0;fault<=0;error_code<=0;loaded_bytes<=0;end
  else if(active_reset)begin state<=IDLE;remaining<=0;chr32<=0;chip<=0;lane<=0;byte_hold<=0;load_address<=0;fault<=0;error_code<=0;loaded_bytes<=0;end
  else if(fault)begin
   // Drain an accepted write even after a bad command; never shorten its pulse.
   if(state==WRITE)begin if(remaining==1)state<=HOLD;else remaining<=remaining-1'b1;end
   else if(state==HOLD)state<=RELEASE;
   else state<=FAILED;
  end else begin
   if((load_begin && (load_end || start || stop || load_valid)) || (load_end && (start || stop || load_valid)) || (start && (stop || load_valid)))fail(5);
   else if(stop)begin if(state==WRITE || state==HOLD)fail(6);else if(state==RUN)state<=READY;else begin state<=IDLE;loaded_bytes<=0;end end
   else if(load_begin)begin
    if(state==IDLE || state==READY)begin state<=RECEIVE;loaded_bytes<=0;chr32<=load_chr32;end else fail(1);
   end else if(start)begin if(state==READY)state<=RUN;else fail(3);end
   else if(load_end)begin if(state==RECEIVE && loaded_bytes==total)state<=READY;else fail(2);end
   else if(load_valid && (state==IDLE || state==READY || state==RUN || (state==RECEIVE && loaded_bytes==total)))fail(4);
   else case(state)
    RECEIVE:if(load_valid && load_ready)begin
     load_address<={2'd0,byte_address[21:2]};chip<=byte_address[1];lane<=byte_address[0];byte_hold<=load_data;
     remaining<=3;state<=SETUP;
    end
    SETUP:state<=WRITE;
    WRITE:if(remaining==1)state<=HOLD;else remaining<=remaining-1'b1;
    HOLD:state<=RELEASE;
    RELEASE:begin loaded_bytes<=loaded_bytes+1'b1;state<=RECEIVE;end
    default:;
   endcase
  end
 end
endmodule
