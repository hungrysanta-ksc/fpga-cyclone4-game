# SPDX-License-Identifier: MIT
"""Decouple qualified CHR reads from the host with one 256x27 M9K FIFO."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import sha,ROOT

def transform(s):
 def replace(a,b):
  nonlocal s
  assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
 replace('IDLE=0,ASK=1,LOOKUP=2,REQUEST=3,WAIT_REPLY=4,STREAM=5;', 'IDLE=0,ASK=1,LOOKUP=2,REQUEST=3,WAIT_REPLY=4,DRAIN=5;')
 replace('reg [15:0] generation;reg [7:0] held_byte;', 'reg [15:0] generation;')
 replace('state==REQUEST || state==STREAM','state==REQUEST || state==DRAIN')
 replace('assign mem_request=operate && state==REQUEST && !mem_response;', 'reg [8:0] fifo_used;\n assign mem_request=operate && state==REQUEST && !mem_response && fifo_used<256;')
 replace('assign byte_valid=operate && state==STREAM;', '''// One producer request at a time reserves a free FIFO entry until reply.
 // Head is a synchronous M9K read; empty->nonempty takes one read edge.
 (* ramstyle="M9K" *) reg [26:0] fifo[0:255];
 reg [26:0] fifo_head;
 reg [7:0] fifo_write,fifo_read;
 reg fifo_valid;
 wire push=operate && state==WAIT_REPLY && mem_response && !mem_error &&
   mem_response_address==mem_address && mem_response_generation==generation;
 wire pop=byte_valid && byte_ready;
 always @(posedge clk)begin
  if(push)fifo[fifo_write]<={kind,tile,lane,mem_data};
  fifo_head<=fifo[pop ? fifo_read+8'd1 : fifo_read];
 end
 always @(posedge clk)begin
  if(reset || clear || start && !busy && !done && !quarantine && mem_idle)begin
   fifo_read<=0;fifo_write<=0;fifo_used<=0;fifo_valid<=0;
  end else begin
   if(push)fifo_write<=fifo_write+1'b1;
   if(pop)fifo_read<=fifo_read+1'b1;
   case({push,pop})
    2'b10:fifo_used<=fifo_used+1'b1;
    2'b01:fifo_used<=fifo_used-1'b1;
    default:;
   endcase
   // Do not expose read-during-write data when replacing the final entry.
   fifo_valid<=fifo_used>1 || (fifo_used==1 && !pop);
  end
 end
 assign byte_valid=operate && fifo_valid && fifo_used!=0;''')
 replace('assign byte_data=held_byte;assign byte_tile=tile;assign byte_lane=lane;\n assign byte_kind=kind;', 'assign byte_data=fifo_head[7:0];assign byte_tile=fifo_head[24:12];assign byte_lane=fifo_head[11:8];\n assign byte_kind=fifo_head[26:25];')
 replace('if(tile==8191)begin busy<=0;done<=1;completed<=1;state<=IDLE;end', 'if(tile==8191)state<=DRAIN;')
 replace('waiting<=0;held_byte<=0;pending<=0;', 'waiting<=0;pending<=0;')
 replace("cycles<=cycles+1'b1;waiting<=waiting+1'b1;", "cycles<=cycles+1'b1;waiting<=waiting+1'b1;\n    if(pop)byte_count<=byte_count+1'b1;")
 replace('REQUEST:if(mem_ready)begin', 'REQUEST:if(mem_ready && fifo_used<256)begin')
 replace('end else begin held_byte<=mem_data;state<=STREAM;end', '''end else begin
       if(lane==15)advance_tile();
       else begin lane<=lane+1'b1;state<=REQUEST;end
      end''')
 replace('''     STREAM:if(byte_ready)begin
      byte_count<=byte_count+1'b1;waiting<=0;
      if(lane==15)advance_tile();
      else begin lane<=lane+1'b1;state<=REQUEST;end
     end''', '''     DRAIN:if(fifo_used==0)begin busy<=0;done<=1;completed<=1;state<=IDLE;end''')
 s=s.replace('// This module is not wired to the production PSRAM arbiter. Its backend must','//171 Buffered producer. The unchanged qualified PSRAM arbiter must')
 return s

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
 m=json.loads((baseline/'preparation.json').read_bytes());pins=dict(m['sources'])
 #169 changed only the SNES ROM via CDB/MIF after the167 preparation manifest.
 pins['sink-program.hex']=sha(baseline/'sink-program.hex')
 for n,h in pins.items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline/n,p)
 n='nes_native_fill165.sv';old=(out/n).read_text();new=transform(old)
 (out/n).write_text(new,encoding='utf-8',newline='\n')
 (out/'prefetch.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf-8')
 result=dict(sources={n:sha(out/n) for n in pins},baseline=pins,changed=[n],public_sources={'tools/nes_prefetch171.py':sha(Path(__file__))},same_limits=True,save_sram_used=False)
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.baseline,a.out)
