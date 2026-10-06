// SPDX-License-Identifier: MIT
// Test-only synchronous ROM backend; no physical PSRAM timing/CDC claim.
// DELAY=1 returns a registered response one clock after accepting a request.
module rom_backend_model(input wire clk,reset,rom_request,input wire [21:0] rom_address,
 output wire rom_ready,output reg rom_response,output wire rom_error,
 output reg [21:0] rom_response_address,output reg [7:0] rom_data);
 reg [7:0] prg[0:65535],chr[0:32767];
 integer delay_cycles,wait_left,accepted=0;reg active=0;reg [21:0] address;
 assign rom_ready=!reset && !active;
 assign rom_error=0;
 initial begin
  integer unused,chr32;
  unused=$value$plusargs("DELAY=%d",delay_cycles);if(delay_cycles<1 || delay_cycles>8)$fatal(1,"invalid delay");
  unused=$value$plusargs("CHR32=%d",chr32);
  $readmemh("prg.hex",prg);$readmemh("chr.hex",chr,0,chr32?32767:16383);
 end
 always @(posedge clk)begin
  rom_response<=0;
  if(reset)begin active<=0;wait_left<=0;rom_response_address<=0;rom_data<=0;end
  else if(active)begin
   if(wait_left==1)begin
    active<=0;rom_response<=1;rom_response_address<=address;
    if(address<22'h10000)rom_data<=prg[address[15:0]];
    else if(address>=22'h200000 && address<22'h208000)rom_data<=chr[address[14:0]];
    else $fatal(1,"bad external address %h",address);
   end else wait_left<=wait_left-1;
  end else if(rom_request && rom_ready)begin active<=1;wait_left<=delay_cycles;address<=rom_address;accepted++;end
 end
endmodule
