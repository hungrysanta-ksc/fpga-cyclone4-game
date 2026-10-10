`timescale 1ns/1ps
// SPDX-License-Identifier: MIT
// 068 diagnostic reader: registered CE/OE-active phase survives one-hot recoding.
// One SETUP, READ_CYCLES ACTIVE, one sample HOLD, one RELEASE before response.
// One outstanding immutable byte read. Common asynchronous reset is mandatory;
// each domain releases reset through two flops. Independent resets are unsupported.
// Bundled address/data require explicit board max-delay constraints before signoff.
module nes_rom_physical #(parameter integer READ_CYCLES=16, EARLY_ACK=0, parameter real REQ_DELAY=5.0, ACK_DELAY=8.0)(
 input wire clk,mem_clk,reset,
 input wire check_mode,check_request,input wire [21:0] check_address,
 output wire check_ready,output reg check_response,
 output wire [21:0] check_response_address,output wire [7:0] check_data,
 input wire rom_request,input wire [21:0] rom_address,
 output wire rom_ready,rom_response,rom_error,
 output wire [21:0] rom_response_address,output wire [7:0] rom_data,
 output reg [21:0] psram_address,
 output wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,
 input wire [15:0] psram_data
);
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] source_reset,memory_reset;
 always @(posedge clk or posedge reset)
  if(reset)source_reset<=2'b11;else source_reset<={source_reset[0],1'b0};
 always @(posedge mem_clk or posedge reset)
  if(reset)memory_reset<=2'b11;else memory_reset<={memory_reset[0],1'b0};
 wire sr=source_reset[1],mr=memory_reset[1];
 //129 The owner changes only across common reader reset. Capture it after
 // local release and delay readiness until capture completes. Raw cancellation
 // still asynchronously clears both the controller and this ownership latch.
 reg owner_valid,owner_check;
 always @(posedge mem_clk or posedge mr)
  if(mr)begin owner_valid<=0;owner_check<=0;end
  else if(!owner_valid)begin owner_valid<=1;owner_check<=check_mode;end
 reg request_toggle,ack_toggle,ack_seen,source_busy;
 wire request_flight,ack_flight;assign #(REQ_DELAY) request_flight=request_toggle;assign #(ACK_DELAY) ack_flight=ack_toggle;
 reg [21:0] address_hold;
 reg [7:0] data_hold;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] request_sync,ack_sync;
 always @(posedge mem_clk or posedge mr)
  if(mr)request_sync<=0;else request_sync<={request_sync[0],request_flight};
 always @(posedge clk or posedge sr)
  if(sr)ack_sync<=0;else ack_sync<={ack_sync[0],ack_flight};
 assign rom_response=!sr && source_busy && ack_sync[1]!=ack_seen;
 assign rom_ready=!sr && (!source_busy || rom_response);
 assign rom_response_address=address_hold;
 assign rom_data=data_hold;
 // A read-only physical memory has no separate error indication. Deadline faults
 // belong to051; pin access/setup violations require board timing validation.
 assign rom_error=0;
 always @(posedge clk or posedge sr)begin
  if(sr)begin request_toggle<=0;ack_seen<=0;source_busy<=0;address_hold<=0;end
  else begin
   if(rom_response)begin ack_seen<=ack_sync[1];source_busy<=0;end
   if(rom_request && rom_ready)begin
    address_hold<=rom_address;request_toggle<=!request_toggle;source_busy<=1;
   end
  end
 end
 localparam CW=$clog2(READ_CYCLES+1);
 reg [CW-1:0] remaining;
 localparam IDLE=0,SETUP=1,ACTIVE=2,HOLD=3,RELEASE=4;
 reg [2:0] state;
 reg chip,lane;
 reg reading_active;
 wire reading=!mr && reading_active;
 assign check_ready=!mr && owner_valid && owner_check && state==IDLE;
 // Reuse the controller address/chip/lane and held data; no second tag RAM.
 assign check_response_address={psram_address[19:0],chip,lane};
 assign check_data=data_hold;
 wire pending=owner_valid && (owner_check ? check_request : request_sync[1]!=ack_toggle);
 wire [21:0] selected_address=owner_check ? check_address : address_hold;
 assign psram_1ce=!(reading && !chip);
 assign psram_2ce=!(reading && chip);
 assign psram_oe=!reading;
 assign psram_we=1'b1;
 assign psram_bhe=1'b0;
 assign psram_ble=1'b0;
 always @(posedge mem_clk or posedge mr)begin
  if(mr)begin state<=IDLE;reading_active<=0;remaining<=0;ack_toggle<=0;data_hold<=0;check_response<=0;psram_address<=0;chip<=0;lane<=0;end
  else begin
   check_response<=0;
   // Keep the pin-active flop unchanged at ACTIVE->HOLD (sample edge).
   if(state==SETUP)reading_active<=1;
   else if(state==HOLD)reading_active<=0;
   case(state)
    IDLE:if(pending)begin
     psram_address<={2'b0,selected_address[21:2]};chip<=selected_address[1];lane<=selected_address[0];
     remaining<=CW'(READ_CYCLES);state<=SETUP;
    end
    SETUP:state<=ACTIVE;
    ACTIVE:begin
     remaining<=remaining-1'b1;
     if(remaining==1)begin
      // Capture while CE/OE stay active for another complete memory clock.
      data_hold<=lane?psram_data[7:0]:psram_data[15:8];state<=HOLD;
     end
    end
    HOLD:begin state<=RELEASE;if(EARLY_ACK && !owner_check)ack_toggle<=request_sync[1];end
    RELEASE:begin
     // Ownership cannot change in response to completion before pin release.
     if(owner_check)check_response<=1;else if(!EARLY_ACK)ack_toggle<=request_sync[1];
     state<=IDLE;
    end
    default:begin state<=IDLE;reading_active<=0;end
   endcase
  end
 end
endmodule
