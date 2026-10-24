# SPDX-License-Identifier: MIT
"""Execute compiled plan-supply priority across BG/OBJ backlog and credit states."""
import argparse,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from nes_delta231 import sha

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 arm=Producer(a.source/'output.elf',None);rows=[]
 for stage,at,end in [('BG',428,594),('BG',536,594),('OBJ',594,661),('drained',661,661)]:
  for cache,flags in [(0,0),(0,1),(1,0),(1,1),(1,2)]:
   for k,v in dict(plan_at267=at,plan_bytes267=end,plan_cache282=cache,plan_flags282=flags).items():arm.uc.mem_write(arm.symbols[k],struct.pack('<I',v))
   want=int(at<end and (not cache or flags&1));actual=arm.call('supply303',[]);assert actual==want
   rows.append(dict(stage=stage,at=at,end=end,cache=cache,flags=flags,supply_first=actual))
 r=dict(passed=True,checks=rows,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope='actual compiled gate; live integration separately required')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))
if __name__=='__main__':main()
