# SPDX-License-Identifier: MIT
"""17-entry physical CHR cache, same request/response boundary as cache192.

No speculative lease or SPI command is granted here. The caller retains those
responsibilities; STOP flushes validity and the existing arbiter drains replies.
"""
from nes_delta231 import once

def apply(d):
 p=d/'nes_chr_cache192.sv';s=p.read_text()
 # 272 used bytes in a physical 512x8 M9K allocation. Charge all 4096 bits.
 # A pending fill prohibits hits; its read-during-write result is not exposed.
 s=once(s,'reg [7:0] bytes[0:15];', '(* ramstyle="M9K, no_rw_check" *) reg [7:0] bytes[0:511];')
 s=once(s,'reg [15:0] valid;reg [17:0] tag;reg [31:0] cached_epoch;', '''reg [15:0] valid[0:16];reg [17:0] tag[0:16];reg [31:0] cached_epoch;
 reg [4:0] replacement,held_slot;
 reg found;reg [4:0] slot;
 always @*begin
  found=0;slot=replacement;
  for(integer j=0;j<17;j=j+1)if(valid[j]!=0&&tag[j]==address[21:4])begin found=1;slot=j;end
 end''')
 s=once(s,'wire hit=tag==address[21:4]&&valid[address[3:0]];', 'wire hit=found&&valid[slot][address[3:0]];')
 s=once(s,'valid<=0;tag<=0;', 'for(integer j=0;j<17;j=j+1)begin valid[j]<=0;tag[j]<=0;end replacement<=0;held_slot<=0;')
 s=once(s,'held_address<=address;held_generation<=generation;', '''held_address<=address;held_generation<=generation;held_slot<=slot;
    if(!found)begin valid[slot]<=0;tag[slot]<=address[21:4];replacement<=replacement==16?0:replacement+1'b1;end''')
 # Fixed synchronous read/write ports; validity, not resetting the data array,
 # owns exposure. Keep this RAM process outside reset/epoch control.
 s=once(s,'hit_data<=bytes[address[3:0]];', 'hit_data<=0;')
 s=once(s,'bytes[held_address[3:0]]<=back_data;', '')
 s=once(s,'assign data=hit_reply?hit_data:back_data;', '''reg [7:0] cache_q;
 always @(posedge clk)begin
  cache_q<=bytes[{slot,address[3:0]}];
  if(!invalidate&&pending&&back_response&&!back_error&&back_response_address==held_address&&back_response_generation==held_generation)
   bytes[{held_slot,held_address[3:0]}]<=back_data;
 end
 assign data=hit_reply?cache_q:back_data;''')
 s=once(s,'tag<=held_address[21:4];', 'tag[held_slot]<=held_address[21:4];')
 s=once(s,"valid<=(tag==held_address[21:4]?valid:16'd0)|(16'd1<<held_address[3:0]);", "valid[held_slot]<=valid[held_slot]|(16'd1<<held_address[3:0]);")
 p.write_text(s,newline='\n')
