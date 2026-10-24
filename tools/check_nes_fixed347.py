# SPDX-License-Identifier: MIT
"""Actual M4 malformed fixed-block repeat/CRC/history checks, no RTL claim."""
import argparse,binascii,json
from nes_delta231 import sha
from pathlib import Path
from probe_nes_arm264 import ARM
from probe_nes_decode280 import records,chunks,golden
from nes_fixed347 import encode347


def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 g,raw=golden(905);rr=encode347(bytes(4398),g,bytes(len(raw)),None,1,1)
 ri=next(i for i,r in enumerate(rr) if r[0]&128 and 32<=(r[0]&127)<68)
 rawi=next(i for i,r in enumerate(rr) if r[0]&128 and 68<=(r[0]&127)<127)
 geo=next(i for i,r in enumerate(rr) if r[:4]==b'\xff\xff\0\3')
 cases=[]
 def reject(name,rs,reset_after=None):
  arm=ARM(a.source/'decoder.elf',None);arm.call('reset280',[])
  if reset_after:
   for block in chunks(reset_after):
    arm.uc.mem_write(0x20018000,block);assert arm.call('block280',[0x20010000,0x20018000,len(block),binascii.crc_hqx(block,65535)])==1
   assert arm.call('complete280',[])==1;arm.call('reset280',[])
  failed=False
  for block in chunks(rs):
   arm.uc.mem_write(0x20018000,block)
   if not arm.call('block280',[0x20010000,0x20018000,len(block),binascii.crc_hqx(block,65535)]):failed=True;break
  assert failed and arm.call('complete280',[])==0,name
  cases.append(name)
 for width in (0,3):reject(f'invalid repeat width {width}',rr[:ri]+[rr[ri][:1]+bytes([width])+rr[ri][2:]])
 reject('truncated repeat16',rr[:ri]+[rr[ri][:1]+b'\x02\0'])
 reject('raw repeat seed outside6bit domain',rr[:rawi]+[rr[rawi][:2]+b'\x40'])
 reject('duplicate block',rr[:ri+1]+[rr[ri]])
 reject('missing cold block',rr[:1]+rr[2:])
 reject('wrong expanded count',rr[:geo]+[rr[geo][:6]+bytes([rr[geo][6]^1])+rr[geo][7:]])
 reject('wrong stream CRC with valid block CRC',rr[:geo]+[rr[geo][:-1]+bytes([rr[geo][-1]^1])])
 reject('wrong ABI version',[rr[0][:2]+b'\x02'+rr[0][3:]])
 reject('warm after reset cannot reuse history',records(a.source/'frame906.records'),records(a.source/'frame905.records'))
 out=dict(passed=True,cases=cases,ELF_sha256=sha(a.source/'decoder.elf'),scope=__doc__)
 (a.out/'result.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n');print(json.dumps(out))
if __name__=='__main__':main()
