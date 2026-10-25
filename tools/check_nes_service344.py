# SPDX-License-Identifier: MIT
"""Actual M4 BG continuation while a published prefix waits; no SPI timing claim."""
import argparse,binascii,json
from pathlib import Path
from check_nes_frontier342 import A
from nes_delta231 import BASE,sha
from probe_nes_decode280 import records,chunks

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--records',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);o=ap.parse_args();o.out.mkdir(parents=True,exist_ok=False)
 rr=records(o.records);geo=next(i for i,r in enumerate(rr) if r[:4]==b'\xff\xff\0\3')
 def init():
  a=A(o.source/'output.elf',None)
  for n in ('reset285','reset280'):a.call(n,[])
  a.uc.mem_write(a.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
  def feed(recs):
   for b in chunks(recs):
    a.uc.mem_write(0x20028000,b);assert a.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])==1
  feed(rr[:geo+1])
  for n in ('expand286','begin285','geometry_plan286','h2early286'):assert a.call(n,[])==1,n
  feed(rr[geo+1:]);assert a.call('input_commit286',[])==1;assert a.call('begin_step286',[])==1
  return a
 def word(a,n):return int.from_bytes(a.uc.mem_read(a.symbols[n],4),'little')
 a=init();b=init();cases=[]
 assert not a.call('bg_done293',[]) and not a.call('pending302',[])
 before=word(a,'calls285');assert a.call('service296',[])==1 and word(a,'calls285')==before;cases.append('no BG wait service before prefix publication')
 for x in (a,b):x.uc.mem_write(x.symbols['prefixes344'],(1).to_bytes(4,'little'))
 assert a.call('pending302',[])==1;steps=[]
 for _ in range(300):
  at=a.instructions;assert a.call('service296',[])==1;steps.append(a.instructions-at)
  assert b.call('next_step286',[])!=0
  for n in ('output_size285','batch_size285','batch_count285','calls285'):assert word(a,n)==word(b,n),n
  for n,z in [('output285',word(a,'output_size285')),('batch285',word(a,'batch_size285'))]:assert bytes(a.uc.mem_read(a.symbols[n],z))==bytes(b.uc.mem_read(b.symbols[n],z))
  if a.call('bg_done293',[]):break
 else:raise AssertionError('BG service did not complete')
 cases.append('actual bounded service steps exactly match foreground BG plans and marker')
 a.call('stop286',[]);assert a.call('service296',[])==0 and a.call('pending302',[])==0;cases.append('STOP cancels BG continuation')
 r=dict(passed=True,cases=cases,steps=len(steps),max_step_instructions=max(steps),ELF_sha256=sha(o.source/'output.elf'),records_sha256=sha(o.records),scope=__doc__)
 (o.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))
if __name__=='__main__':main()
