# SPDX-License-Identifier: MIT
"""Run the actual wait helper at a committed BG boundary under plan credit states."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_decode280 import records,chunks
from guard_nes_irq284 import Endpoint
from nes_delta231 import BASE,sha

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 ep=Endpoint();arm=Producer(a.source/'output.elf',ep);ep.arm=arm
 for n in ('irq_init284','reset259','reset285','reset280'):arm.call(n,[])
 arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
 def word(n):return int.from_bytes(arm.uc.mem_read(arm.symbols[n],4),'little')
 def put(n,v):arm.uc.mem_write(arm.symbols[n],struct.pack('<I',v))
 for b in chunks(records(BASE/'probes/nes-joint284/test04/frame905.records')):
  arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
 for n in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):assert arm.call(n,[])
 for _ in range(2048):
  assert arm.call('next_step286',[])
  if arm.call('bg_done293',[]):break
 else:raise AssertionError('BG never complete')
 assert arm.call('pending302',[]);end=word('output_size285');snapshot=bytes(arm.uc.mem_read(0x20000000,0x40000));context=arm.uc.context_save();rows=[]
 for label,at,cache,flags,phase,sent,retired,compute in [('BG writable',428,1,1,0,4,0,False),('BG unknown',428,0,0,0,4,0,False),('BG full',428,1,0,0,4,0,True),('prefix drained',end,1,1,0,4,0,True),('DMA ready',end,1,1,2,4,0,False),('queue free',end,1,1,0,3,0,False),('wrapped queue full',428,1,0,0,1,65533,True)]:
  arm.uc.mem_write(0x20000000,snapshot);arm.uc.context_restore(context);arm.gpio(0)
  for n,v in dict(plan_at267=at,plan_bytes267=end,plan_cache282=cache,plan_flags282=flags,phase_ready302=phase,wait_reason302=8).items():put(n,v)
  arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired));before=arm.instructions
  assert arm.call('work302',[])==1
  changed=bool(word('obj_init302'));assert changed==compute,(label,changed,compute)
  rows.append(dict(case=label,computed=changed,instructions=arm.instructions-before,output_before=end,output_after=word('output_size285')))
 r=dict(passed=True,checks=rows,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope='Actual compiled work302 at committed BG; memory-controlled credit inputs; not live SPI')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))
if __name__=='__main__':main()
