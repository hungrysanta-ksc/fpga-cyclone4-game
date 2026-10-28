# SPDX-License-Identifier: MIT
"""Specialize away the unused required-bitmap port; retain all fetch checks."""
import json,shutil
from nes_delta231 import ROOT,sha,once
from nes_hint367 import COMMON as PREVIOUS
COMMON=PREVIOUS+('nes_native_planes165.sv','nes_native_frame201.sv')

def materialize(d):
 root=ROOT/'src/fpga/nes_source368';m=json.loads((root/'manifest.json').read_text())
 for n,h in m['source_files'].items():assert sha(root/n)==h;shutil.copyfile(root/n,d/n)

def functional(d):
 materialize(d);p=d/'joint266_tb.sv';s=p.read_text()
 s=once(s,'#(.EARLY_RELEASE(1)) frame(', '#(.EARLY_RELEASE(1),.REQUIRED_BITMAP(0)) frame(')
 s=once(s,' task clear_output;', '''
 reg [7:0] query_kinds368=0;
 always @(posedge clk)if(!reset&&query)begin
  query_kinds368[query_kind]<=1;
  if(query_kind==6)$fatal(1,"source attempted removed query6 port368");
 end
 final $display("QUERY368 kinds=%02x",query_kinds368);
 task clear_output;''')
 s=s.replace('if(!capture_begin)$fatal(1,"next capture deadline missed367 frame%0d",free_id367);',
  'if(!capture_begin)$fatal(1,"next capture deadline missed367 frame%0d owned%0d initialized%0d release%0d fault%0d",free_id367,owned,initialized,release_frame,lease_fault);')
 p.write_text(s,newline='\n')

def board(d):
 materialize(d);p=d/'nes_live_joint.sv';s=p.read_text()
 s=once(s,'#(.EARLY_RELEASE(1)) native_frame(', '#(.EARLY_RELEASE(1),.REQUIRED_BITMAP(0)) native_frame(')
 p.write_text(s,newline='\n')
