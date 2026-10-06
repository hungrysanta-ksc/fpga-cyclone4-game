"""Original NMI/IRQ priority stimuli. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,json,hashlib
MODES=[('not_taken',0x40,0x60,False,2),('forward',0x40,0x60,True,3),('backward',0x80,0x60,True,3),('cross_forward',0xf0,0x110,True,4),('cross_backward',0x110,0xf0,True,4)]
def build(out):
 out.mkdir(parents=True,exist_ok=False);prg=bytearray([0xea])*32768;used=set();cases=[]
 def put(a,data):
  for i,v in enumerate(data):
   assert 0x8000<=a+i<65536 and a+i not in used
   used.add(a+i);prg[a+i-0x8000]=v
 def jmp(a):return [0x4c,a&255,a>>8]
 put(0x8000,[0x78,0xd8,0xa2,255,0x9a,0xa9,0,0x8d,0,0x20,0x8d,1,0x20,0x8d,0x15,0x40,0x85,3,0xa9,0x40,0x8d,0x17,0x40]+jmp(0x8200))
 for mode,b,t,taken,cycles in [MODES[0],MODES[1],MODES[3]]:
  scenarios=[(True,False,start) for start in range(-1,11)]+[(False,False,0),(True,True,0)]
  for irq_enabled,masked,nmi_start in scenarios:
   n=len(cases)+1;base=0x8200+(n-1)*0x200;branch=base+b;target=base+t;following=target if taken else branch+2;nextcase=base+0x200 if n<42 else 0xfa00;flags=(0x22 if taken else 0x20)|(4 if masked else 0)
   put(base,[0x78,0xa9,n,0x85,0,0xa9,flags,0x48,0x28]+jmp(branch))
   put(branch,[0xf0,(target-branch-2)&255]);put(following,[0xea]*6+[0x78]+jmp(nextcase))
   put(0xf000+(n-1)*8,[branch&255,branch>>8,nmi_start&255,int(irq_enabled),cycles,0,0,0])
   cases.append(dict(id=n,mode=mode,branch=branch,target=target,next_pc=following,taken=taken,cycles=cycles,flags=flags,nmi_start_cycle=nmi_start,nmi_width=2,irq_enabled=irq_enabled,irq_masked=masked))
 assert len(cases)==42
 put(0xfa00,[0x78,0xa9,255,0x85,0]+jmp(0xfa05))
 put(0xfb00,[0x48,0xe6,3,0xa9,0,0x85,2,0x68,0x40])
 put(0xfc00,[0x48,0xe6,4,0x68,0x40])
 for a in (0xfffa,0xfffc,0xfffe):put(a,(0x8000 if a==0xfffc else (0xfc00 if a==0xfffa else 0xfb00)).to_bytes(2,'little'))
 chrdata=bytes(8192);rom=b'NES\x1a'+bytes([2,1])+bytes(10)+prg+chrdata;(out/'interrupt-priority.nes').write_bytes(rom)
 for name,data in [('prg',prg),('chr',chrdata)]: (out/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data))
 m=dict(original_diagnostic=True,license='MIT',mapper=0,prg_bytes=32768,chr_bytes=8192,sha256=hashlib.sha256(rom).hexdigest(),cases=cases)
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print('Built',len(cases),'NMI/IRQ scenarios',m['sha256'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
