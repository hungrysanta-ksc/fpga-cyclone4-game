# SPDX-License-Identifier: MIT
"""048 combine mutually exclusive row-copy and CPU writes before lane address decoding."""
from pathlib import Path
import json,sys
import nes_oam_banked as base
original_bank=base.bank_ppu

def compact(text):
 s=original_bank(text)
 for i in range(8):
  old=f""" if(!reset && ce)begin
  if(((~old_rendering && rendering) || corrupting_write) && ~PAL &&
     ((old_using_secondary != using_secondary) || corrupting_write))
   oam_bank{i}[oam_row_cur]<=oam_bank{i}[oam_row_last];
  if(oam_data_write && !rendering && oam_read_addr[2:0]==3'd{i})
   oam_bank{i}[oam_read_addr[7:3]]<=is_attr_byte ? (oam_din & 8'hE3) : oam_din;
 end"""
  new=f""" if(oam_copy_write || (oam_cpu_write && oam_read_addr[2:0]==3'd{i}))
  oam_bank{i}[oam_write_row]<=oam_copy_write ? oam_bank{i}[oam_row_last] :
   (is_attr_byte ? (oam_din & 8'hE3) : oam_din);"""
  assert s.count(old)==1;s=s.replace(old,new)
 anchor='// Original048 structural mapping:'
 wires="""// A rendering-rise row copy and a non-rendering CPU write are mutually exclusive.
// corrupting_write is pinned to zero in this upstream core. Reject other variants.
wire oam_copy_write=!reset && ce && ((~old_rendering && rendering) || corrupting_write) && ~PAL &&
 ((old_using_secondary != using_secondary) || corrupting_write);
wire oam_cpu_write=!reset && ce && oam_data_write && !rendering;
wire [4:0] oam_write_row=oam_copy_write ? oam_row_cur : oam_read_addr[7:3];
"""
 assert 'assign corrupting_write = 0;' in s and s.count(anchor)==1
 return s.replace(anchor,wires+'\n'+anchor)

def main():
 out=Path(sys.argv[sys.argv.index('--out')+1]);base.bank_ppu=compact;base.main()
 p=out/'result.json';m=json.loads(p.read_text());m['optimization']='merged_mutually_exclusive_normal_write_port';m['optimization_driver_sha256']=base.live.sha(Path(__file__));base.live.put(p,json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
