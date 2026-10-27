# SPDX-License-Identifier: MIT
"""Directed equivalent ABI: replace cold905 zero-tail shortcut by general
repeat16 of the SAME1100zero bytes;wire CRC adjusted,source oracle unchanged."""
import argparse,json,shutil
from pathlib import Path
from probe_nes_arm264 import crc
from probe_nes_jobs394_arm import decode
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 for f in a.arm.glob('*.json'):shutil.copyfile(f,a.out/f.name)
 wire=[bytearray.fromhex(s)for s in json.loads((a.out/'wire905.json').read_text())];changed=0
 for w in wire:
  if w[1]==0x90 and w[20]==5 and w[17]&64:
   w[17]&=~64;w[-2:]=crc(w[:-2]).to_bytes(2,'big');changed+=1
 assert changed==1
 (a.out/'wire905.json').write_text(json.dumps([w.hex()for w in wire],indent=2)+'\n')
 jobs=decode([bytes(w[1:-2])for w in wire]);(a.out/'jobs905.json').write_text(json.dumps(jobs,indent=2)+'\n')
 print('Prepared equivalent1100B general repeat;production512B internal fragments required')
if __name__=='__main__':main()
