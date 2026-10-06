"""Original OAM DMA pages, wrapping addresses and parity padding. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,json,hashlib

def pattern(page,i):return ((i*73)^(i>>1)^(0x5a if page==2 else 0xa7))&255

def build(out):
 out.mkdir(parents=True,exist_ok=False);prg=bytearray([0xea])*32768;code=bytearray();cases=[]
 def emit(*v):code.extend(v)
 def sta(a):emit(0x8d,a&255,a>>8)
 emit(0x78,0xd8,0xa2,255,0x9a,0xa9,0);sta(0x2000);sta(0x2001);sta(0x4015);emit(0x85,0x10,0xa9,0x40);sta(0x4017)
 emit(0xa2,0);loop=0x8000+len(code)
 emit(0xbd,0,0xe0,0x9d,0,2,0xbd,0,0xe1,0x9d,0,3,0xe8,0xd0);emit((loop-(0x8000+len(code)+1))&255)
 emit(0x24,0) # Align first DMA pair with the later pairs; 3-cycle parity pad.
 for page in (2,3):
  for start in (0,1,252,255):
   for pad in (0,1):
    n=len(cases)+1;emit(0xa9,n,0x85,0,0xa9,start);sta(0x2003)
    if pad:emit(0x24,0)
    else:emit(0xea)
    emit(0xa9,page);trigger=0x8000+len(code);sta(0x4014);resume=0x8000+len(code);emit(0xe6,0x10,0xa9,n,0x85,0x20)
    cases.append(dict(id=n,page=page,oam_start=start,padding=pad,trigger_pc=trigger,resume_pc=resume))
 emit(0xa9,255,0x85,0);end=0x8000+len(code);emit(0x4c,end&255,end>>8);prg[:len(code)]=code
 for page in (2,3):prg[0x6000+(page-2)*256:0x6100+(page-2)*256]=bytes(pattern(page,i) for i in range(256))
 prg[0x1000]=0x40
 for a in (0x7ffa,0x7ffc,0x7ffe):prg[a:a+2]=(0x8000 if a==0x7ffc else 0x9000).to_bytes(2,'little')
 rom=b'NES\x1a'+bytes([2,1])+bytes(10)+prg+bytes(8192);(out/'oam-dma.nes').write_bytes(rom)
 for name,data in [('prg',prg),('chr',bytes(8192))]:(out/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data))
 m=dict(original_diagnostic=True,license='MIT',mapper=0,prg_bytes=32768,chr_bytes=8192,sha256=hashlib.sha256(rom).hexdigest(),cases=cases);(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print('Built',len(cases),'OAM DMA cases',m['sha256']);return m
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
