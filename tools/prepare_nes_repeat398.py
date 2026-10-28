# SPDX-License-Identifier: MIT
"""Equivalent 1100 zero bytes via repeat32, exercising the same 512B reserve.
Only the wire seed/codec changes; the independent canonical oracle is retained.
"""
import argparse,json,shutil,struct
from pathlib import Path
from probe_nes_arm264 import crc
from probe_nes_jobs394_arm import decode
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 for q in a.arm.glob('*.json'):shutil.copyfile(q,a.out/q.name)
 wire=[bytearray.fromhex(x)for x in json.loads((a.out/'wire905.json').read_text())];changed=0
 for w in wire:
  if w[1]==0x90 and w[20]==5 and not w[17]&64 and (w[17]>>2)&3==2 and int.from_bytes(w[15:17],'little')==1100:
   assert w[-4:-2]==bytes(2);w[17]=(w[17]&~12)|12;w[-2:-2]=bytes(2);w[9:11]=struct.pack('<H',len(w)-13);w[-2:]=crc(w[:-2]).to_bytes(2,'big');changed+=1
 assert changed==1
 (a.out/'wire905.json').write_text(json.dumps([w.hex()for w in wire],indent=2)+'\n')
 (a.out/'jobs905.json').write_text(json.dumps(decode([bytes(w[1:-2])for w in wire]),indent=2)+'\n')
 print('Prepared equivalent1100B repeat32;512B internal fragments required')
if __name__=='__main__':main()
