"""Original 6502 branch bus diagnostic. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,json,hashlib
OPS=[('BCC',0x90,1,False),('BCS',0xb0,1,True),('BEQ',0xf0,2,True),('BNE',0xd0,2,False),('BMI',0x30,128,True),('BPL',0x10,128,False),('BVC',0x50,64,False),('BVS',0x70,64,True)]
MODES=[('not_taken',0x40,0x60,False),('forward',0x40,0x60,True),('backward',0x80,0x60,True),('cross_forward',0xf0,0x110,True),('cross_backward',0x110,0xf0,True),('offset_127',0x80,0x101,True),('offset_minus128',0xfe,0x80,True)]
def build(out):
 out.mkdir(parents=True,exist_ok=False);prg=bytearray([0xea])*32768;cases=[];used=set()
 def put(a,data):
  for i,v in enumerate(data):
   assert 0x8000<=a+i<0x10000 and a+i not in used
   used.add(a+i);prg[a+i-0x8000]=v
 def jmp(a):return [0x4c,a&255,a>>8]
 put(0x8000,[0x78,0xd8,0xa2,0xff,0x9a,0xa9,0,0x8d,0,0x20,0x8d,1,0x20,0x8d,0x15,0x40,0xa9,0x40,0x8d,0x17,0x40]+jmp(0x8200))
 for name,opcode,mask,positive in OPS:
  for mode,b,t,taken in MODES:
   number=len(cases)+1;base=0x8200+(number-1)*0x200;branch=base+b;target=base+t;nextcase=base+0x200 if number<56 else 0xf800
   flags=0x24 | (mask if positive==taken else 0)
   put(base,[0xa9,number,0x85,0,0xa9,flags,0x48,0x28]+jmp(branch))
   offset=target-(branch+2);assert -128<=offset<=127
   put(branch,[opcode,offset&255]);put(branch+2,jmp(nextcase));put(target,jmp(nextcase))
   cross=((branch+2)&0xff00)!=(target&0xff00)
   dummy=[branch+2]+([((branch+2)&0xff00)|(target&255)] if cross else []) if taken else []
   cases.append(dict(id=number,name=name,mode=mode,opcode=opcode,flags=flags,branch=branch,target=target,taken=taken,offset=offset,cycles=2+len(dummy),dummy_reads=dummy,next_pc=target if taken else branch+2))
 put(0xf800,[0xa9,255,0x85,0]+jmp(0xf804));put(0xf810,[0x40])
 for a in (0xfffa,0xfffc,0xfffe):put(a,((0x8000 if a==0xfffc else 0xf810)).to_bytes(2,'little'))
 chrdata=bytes(8192);rom=b'NES\x1a'+bytes([2,1])+bytes(10)+prg+chrdata
 (out/'branch.nes').write_bytes(rom)
 for name,data in [('prg',prg),('chr',chrdata)]: (out/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data))
 m=dict(original_diagnostic=True,license='MIT',mapper=0,prg_bytes=32768,chr_bytes=8192,sha256=hashlib.sha256(rom).hexdigest(),cases=cases)
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=build(a.out);print('Built',len(m['cases']),'original branch cases',m['sha256'])
