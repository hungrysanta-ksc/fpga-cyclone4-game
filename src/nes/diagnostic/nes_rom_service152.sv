// SPDX-License-Identifier: MIT
// Original051 live-address early immutable ROM service. All ports use NES master clk.
// Geometry: 256KiB PRG +128KiB CHR (fixed SMB3 target). Shared backend, one outstanding read.
// rom_request is a grant strobe ONLY when rom_ready, not a held valid signal.
// Backend must return address/data at least one edge AFTER acceptance, and flush
// pending replies on common reset. No asynchronous clock crossing is implemented.
module nes_rom_early(
 input wire clk,reset,
 input wire ppu_prefetch_valid,input wire [21:0] ppu_prefetch_address,
 input wire cpu_address_valid,ppu_address_valid,
 input wire [24:0] cpumem_addr,input wire cpumem_read,cpu_sample,
 input wire [21:0] ppumem_addr,input wire ppumem_read,ppu_sample,
 output wire [7:0] cpu_data,ppu_data,output wire cpu_valid,ppu_valid,
 input wire rom_ready,output wire rom_request,output wire [21:0] rom_address,
 input wire rom_response,rom_error,input wire [21:0] rom_response_address,input wire [7:0] rom_data,
 output wire fault_trigger,output wire [63:0] fault_context,
 output reg fault,output reg [3:0] error_code
);
 reg busy,pending_ppu;reg [21:0] pending_address;reg [7:0] age;
 reg ppu_previous_cached;reg [16:0] ppu_previous_tag;reg [7:0] ppu_previous_byte;
 reg [7:0] cpu_line_valid;reg [14:0] cpu_line_tag[0:7];reg [7:0] cpu_line_byte[0:7];integer cache_index141;
 reg cpu_cached,ppu_cached;reg [17:0] cpu_tag;reg [16:0] ppu_tag;reg [7:0] cpu_byte,ppu_byte;
 wire cpu_rom=cpumem_addr<25'h40000;
 wire ppu_rom=ppumem_addr>=22'h200000 && ppumem_addr<22'h220000;
 wire response_ok=busy && rom_response && !rom_error && rom_response_address==pending_address;
 wire cpu_reply=response_ok && !pending_ppu && pending_address==cpumem_addr[21:0];
 wire ppu_reply=response_ok && pending_ppu && pending_address==ppumem_addr;
 assign cpu_valid=!reset && !fault && cpu_rom && ((cpu_line_valid[cpumem_addr[2:0]] && cpu_line_tag[cpumem_addr[2:0]]==cpumem_addr[17:3]) || cpu_reply);
 wire ppu_previous_hit=ppu_previous_cached && ppu_previous_tag==ppumem_addr[16:0];
 assign ppu_valid=!reset && !fault && ppu_rom && ((ppu_cached && ppu_tag==ppumem_addr[16:0]) || ppu_previous_hit || ppu_reply);
 assign cpu_data=cpu_reply?rom_data:cpu_line_byte[cpumem_addr[2:0]];
 assign ppu_data=ppu_reply?rom_data:((ppu_cached && ppu_tag==ppumem_addr[16:0])?ppu_byte:ppu_previous_byte);
 wire cpu_pending=busy && !pending_ppu && pending_address==cpumem_addr[21:0];
 wire ppu_pending=busy && pending_ppu && pending_address==ppumem_addr;
 wire cpu_need=(cpumem_read || cpu_address_valid) && cpu_rom && !cpu_valid && !cpu_pending;
 wire ppu_need=(ppumem_read || ppu_address_valid) && ppu_rom && !ppu_valid && !ppu_pending;
 // Use only addresses currently exported by the live core. Immutability permits
 // an early read before the data strobe; tags still check the eventual address.
 // Actual demand outranks an early-only request. PPU wins equal priority.
 wire choose_ppu=ppu_need && (!cpu_need || ppumem_read || !cpumem_read);
 //147 Idle-slot speculation. A misprediction can only fill an immutable
 // physical-address-tagged cache entry. Actual demand wins; no read abort,
 // relaxed sampling deadline or CPU/PPU clock stretching is introduced.
 wire prefetch_hit=(ppu_cached && ppu_tag==ppu_prefetch_address[16:0]) ||
                   (ppu_previous_cached && ppu_previous_tag==ppu_prefetch_address[16:0]);
 wire prefetch_need=ppu_prefetch_valid && ppu_prefetch_address>=22'h200000 &&
   ppu_prefetch_address<22'h220000 && !prefetch_hit;
 wire use_prefetch=!ppu_need && !cpu_need && prefetch_need;
 // Never steal or abort a read already accepted by the backend.
 assign rom_request=!reset && !fault && rom_ready && (!busy || response_ok) && (ppu_need || cpu_need || use_prefetch);
 assign rom_address=rom_request?(use_prefetch?ppu_prefetch_address:(choose_ppu?ppumem_addr:cpumem_addr[21:0])):pending_address;
 //139 Parallel observation only. Capture on the SAME edge that sets fault.
 assign fault_trigger=!reset && !fault && (
  (rom_response && (!busy || rom_response_address!=pending_address || rom_error)) ||
  (busy && !rom_response && age==255) ||
  (ppu_sample && ppu_rom && !ppu_valid) || (cpu_sample && cpu_rom && !cpu_valid));
 //152 The top bit tags the low25 field. PPU sample failures carry the
 // actual current PPU demand, separately from the outstanding request.
 // All service decisions, deadlines, caches and reader pins are unchanged.
 wire context_ppu=ppu_sample && ppu_rom && !ppu_valid;
 assign fault_context={context_ppu,busy,pending_ppu,rom_ready,rom_response,cpu_sample,ppu_sample,cpu_valid,ppu_valid,age,pending_address,
                      context_ppu?{3'b000,ppumem_addr}:cpumem_addr};
 always @(posedge clk or posedge reset)begin
  if(reset)begin
   busy<=0;pending_ppu<=0;pending_address<=0;age<=0;
   cpu_line_valid<=0;
   for(cache_index141=0;cache_index141<8;cache_index141=cache_index141+1)begin cpu_line_tag[cache_index141]<=0;cpu_line_byte[cache_index141]<=0;end
   ppu_previous_cached<=0;ppu_previous_tag<=0;ppu_previous_byte<=0;
   cpu_cached<=0;ppu_cached<=0;cpu_tag<=0;ppu_tag<=0;cpu_byte<=0;ppu_byte<=0;fault<=0;error_code<=0;
  end else if(!fault)begin
   if(busy)age<=age+1'b1;
   if(response_ok)begin
    busy<=0;
    //141 Keep the preceding immutable CHR byte across alternating low/high
    // pattern-plane reads. Only validated replies fill either entry; common
    // reset invalidates both. Physical address tags preserve mapper isolation.
    if(pending_ppu)begin
     ppu_previous_cached<=ppu_cached;ppu_previous_tag<=ppu_tag;ppu_previous_byte<=ppu_byte;
     ppu_cached<=1;ppu_tag<=pending_address[16:0];ppu_byte<=rom_data;end
    //141 Eight direct-mapped immutable PRG bytes relieve repeated instruction
    // fetches. Full physical tags, validated replies, common-reset invalidation.
    else begin
     cpu_line_valid[pending_address[2:0]]<=1;cpu_line_tag[pending_address[2:0]]<=pending_address[17:3];cpu_line_byte[pending_address[2:0]]<=rom_data;
     cpu_cached<=1;cpu_tag<=pending_address[17:0];cpu_byte<=rom_data;end
   end
   if(rom_request)begin busy<=1;pending_ppu<=choose_ppu || use_prefetch;pending_address<=rom_address;age<=0;end
   // One registered sticky cause. Deadline failure never stalls or slows NES.
   if(rom_response && !busy)begin fault<=1;error_code<=3;end
   else if(rom_response && rom_response_address!=pending_address)begin fault<=1;error_code<=4;end
   else if(rom_response && rom_error)begin fault<=1;error_code<=5;end
   else if(busy && !rom_response && age==255)begin fault<=1;error_code<=6;end
   else if(ppu_sample && ppu_rom && !ppu_valid)begin fault<=1;error_code<=2;end
   else if(cpu_sample && cpu_rom && !cpu_valid)begin fault<=1;error_code<=1;end
  end
 end
endmodule
