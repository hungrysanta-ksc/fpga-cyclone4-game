# SPDX-License-Identifier: MIT
"""Same PPU drives old/new planes: exact native event equality outside raw rows."""
import argparse,json
from pathlib import Path
import test_nes_capture501 as candidate
base=candidate.base

def prepare(a):
 candidate.prepare(a)
 old=(a.board/'nes_native_planes165.sv').read_text().replace('module nes_native_planes165(', 'module planes501_reference(')
 (a.out/'planes501_reference.sv').write_text(old)
 p=a.out/'capture500_tb.sv';s=p.read_text()
 s=s.replace(' reg [5:0] pixels[0:57343];',"""
 wire old_event;wire [63:0] old_data;wire [7:0] old_errors501;
 planes501_reference reference(.clk(clk),.reset(reset),.release_scene(stop_request),.ppu_ce(ce),.rom_fault(1'b0),
 .scanline(scanline),.dot(cycle),.bg_low(bg_low),.bg_high(bg_high),.obj_low(obj_low),.obj_high(obj_high),
 .obj_valid(obj_valid),.extra_sprites(1'b0),.bg_attribute(bg_attribute),.obj_attribute(obj_attribute),.obj_x(obj_x),
 .ppu_read(vram_read),.ppu_valid(1'b1),.logical_address(vram_addr),.physical_address(22'h200000+{9'd0,vram_addr[12:0]}),
 .query(1'b0),.query_tile(13'd0),.event_valid(old_event),.event_data(old_data),.errors(old_errors501));
 integer old_count[0:223],new_count[0:223];reg patched[0:223];
 reg [63:0] old_events[0:28671],new_events[0:28671];integer native_rows=0,native_events=0;
 initial for(integer r=0;r<224;r++)begin old_count[r]=0;new_count[r]=0;patched[r]=0;end
 always @(negedge clk)begin
  if(old_event)begin
   if($isunknown(old_data) || old_data[32:25]>=224 || old_count[old_data[32:25]]>=128)$fatal(1,"reference event overflow");
   old_events[old_data[32:25]*128+old_count[old_data[32:25]]]=old_data;old_count[old_data[32:25]]++;
  end
  if(capture.fetch_event)begin
   if($isunknown(capture.fetch_data) || capture.fetch_data[32:25]>=224 || new_count[capture.fetch_data[32:25]]>=128)$fatal(1,"candidate event overflow");
   new_events[capture.fetch_data[32:25]*128+new_count[capture.fetch_data[32:25]]]=capture.fetch_data;
   new_count[capture.fetch_data[32:25]]++;
  end
  if(capture.row_commit)patched[capture.committed_row]=capture.row_patched;
 end
 reg [5:0] pixels[0:57343];""")
 s=s.replace('  $display("RESULT500',"""  for(integer r=0;r<224;r++)if(!patched[r])begin
   if(old_count[r]!=new_count[r])$fatal(1,"native row count mismatch %0d",r);
   for(integer i=0;i<old_count[r];i++)if(old_events[r*128+i]!==new_events[r*128+i])$fatal(1,"native event mismatch %0d/%0d",r,i);
   native_rows++;native_events+=old_count[r];
  end
  $display("EQUIV501 native_rows=%0d native_events=%0d old_errors=%02h",native_rows,native_events,old_errors501);
  $display("RESULT500""")
 p.write_text(s);m=json.loads((a.out/'inputs.json').read_text());m['sources']['planes501_reference.sv']=base.sha(a.out/'planes501_reference.sv');m['testbench_SHA256']=base.sha(p)
 (a.out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
 for n in ['board','reference','out','questa-bin']:p.add_argument('--'+n,type=Path)
 p.add_argument('--focus',default='baseline,f620-addr1-d3,f699-addr1-d0,f699-addr1-d5')
 p.add_argument('--edges',action='store_true')
 a=p.parse_args();a.guards=False;a.phase_sweep=True;a.guard_list=None
 if a.mode=='prepare':prepare(a)
 else:
  base.FILES.append('planes501_reference.sv');candidate.run(a)
