"""Original read/write/branch RDY scenarios. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,json,hashlib
SHAPES=[('memory',0x40,0x40,k) for k in (0,1,2,5,8,9,10)]+[('branch_same',0x40,0x60,k) for k in range(3)]+[('branch_cross',0xf0,0x110,k) for k in range(4)]
def build(out):
 out.mkdir(parents=True,exist_ok=False);prg=bytearray([0xea])*32768;used=set();cases=[]
 def put(a,data):
  for i,v in enumerate(data):
   assert 0x8000<=a+i<65536 and a+i not in used
   used.add(a+i);prg[a+i-0x8000]=v
 def jmp(a):return [0x4c,a&255,a>>8]
 put(0x8000,[0x78,0xd8,0xa2,255,0x9a,0xa9,0,0x8d,0,0x20,0x8d,1,0x20,0x8d,0x15,0x40,0xa9,0x40,0x8d,0x17,0x40]+jmp(0x8200))
 for shape,b,t,stall in SHAPES:
  for mode in range(4):
   n=len(cases)+1;base=0x8200+(n-1)*0x200;anchor=base+b;target=base+t;nextcase=base+0x200 if n<56 else 0xfa00
   put(base,[0x78,0xa9,n,0x85,0,0xa9,0x5a,0x85,0x10,0xa9,0,0x85,0x11,0xa9,7,0x85,0x12,0xa9,0x22,0x48,0x28]+jmp(anchor))
   if shape!='memory':put(anchor,[0xf0,(target-anchor-2)&255])
   put(target,[0xa5,0x10,0x85,0x11,0xe6,0x12]+[0xea]*6+[0x78,0xa9,n,0x85,0x20]+jmp(nextcase))
   put(0xf400+(n-1)*8,[anchor&255,anchor>>8,stall,mode,3,0,0,0]);cases.append(dict(id=n,shape=shape,anchor=anchor,target=target,stall_cycle=stall,stall_length=3,interrupt_mode=mode))
 put(0xfa00,[0x78,0xa9,255,0x85,0]+jmp(0xfa05));put(0xfb00,[0x48,0xe6,3,0xa9,0,0x85,2,0x68,0x40]);put(0xfc00,[0x48,0xe6,4,0x68,0x40])
 for a in (0xfffa,0xfffc,0xfffe):put(a,(0x8000 if a==0xfffc else (0xfc00 if a==0xfffa else 0xfb00)).to_bytes(2,'little'))
 rom=b'NES\x1a'+bytes([2,1])+bytes(10)+prg+bytes(8192);(out/'rdy.nes').write_bytes(rom)
 for name,data in [('prg',prg),('chr',bytes(8192))]:(out/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data))
 m=dict(original_diagnostic=True,license='MIT',mapper=0,prg_bytes=32768,chr_bytes=8192,sha256=hashlib.sha256(rom).hexdigest(),cases=cases);(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print('Built',len(cases),'paired RDY scenarios',m['sha256'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
