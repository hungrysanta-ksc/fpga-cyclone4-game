# SPDX-License-Identifier: MIT
"""Actual M4 differential preparation, malformed geometry and inactive tails."""
import argparse,json
from pathlib import Path
from probe_nes_arm264 import ARM,ELFFile
from probe_nes_decode280 import golden
from nes_delta231 import BASE,sha

def objects(p):
 with p.open('rb') as f:
  return {s.name:(s['st_value'],s['st_size']) for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_OBJECT' and 0x20000000<=s['st_value']<0x20040000}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-raw352/fixed02';elf=a.source/'output.elf';syms=objects(old/'output.elf');assert syms==objects(elf),'RAM ABI changed: snapshots require relocation'
 snapshot=(old/'precommit352-3.bin').read_bytes();rows=[]
 def run(image,data,poison=False):
  arm=ARM(image,None);arm.uc.mem_write(0x20000000,snapshot);arm.uc.mem_write(arm.symbols['history286'],bytes(data))
  before=arm.instructions;ok=arm.call('expand286',[]);cost=arm.instructions-before
  state=bytearray(arm.uc.mem_read(*syms['input285']))
  counts=[int.from_bytes(data[4385+i*2:4387+i*2],'little') for i in range(6)]
  if ok:
   # Prefix lengths are the ABI; tail bytes intentionally have no meaning.
   for off,width,count,cap in ((0,2,counts[0],1056),(2400,8,counts[2],128),(5216,4,counts[3],128)):
    lo=off+width*count;hi=off+width*cap
    state[lo:hi]=bytes(hi-lo)
    if poison:arm.uc.mem_write(arm.symbols['input285']+lo,bytes([0xa5])*(hi-lo))
   arm.uc.mem_write(arm.symbols['ctx286']+119,b'\0')
   plan=arm.call('geometry_plan286',[])
   h2=arm.call('h2early286',[]) if plan else 0
  else:plan=h2=0;state=b''
  error=bytes(arm.uc.mem_read(arm.symbols['expansion_error286'],4))
  output={n:bytes(arm.uc.mem_read(*syms[n])) for n in ('video285','certificate286')} if plan else {}
  return (ok,plan,h2,bytes(state),error,output),cost
 for frame in range(905,976):
  g,r=golden(frame);data=g+r
  b,bc=run(old/'output.elf',data);n,nc=run(elf,data,True)
  assert b==n,(frame,'differential state/output');assert b[0:3]==(1,1,1),(frame,b[:3])
  rows.append(dict(frame=frame,baseline=bc,candidate=nc,saved=bc-nc,inactive_tail_poison=True))
 g,r=golden(907);base=bytearray(g+r);cases=[];directed=[]
 for label,mapcount,objs,exceptions in [('minimum',33,0,0),('maximum',1056,128,128),('exception one',957,8,1)]:
  data=base.copy();data[4385:4387]=mapcount.to_bytes(2,'little');data[4389:4391]=objs.to_bytes(2,'little');data[4391:4393]=exceptions.to_bytes(2,'little')
  if mapcount==33:
   for y in range(224):data[2112+y]&=7
  for i in range(objs):data[2336+i*8:2344+i*8]=bytes(8)
  positions=[y*33+x for y in range(224) if not(int.from_bytes(data[3872+y*2:3874+y*2],'little')&1024) for x in range(33)]
  for i in range(exceptions):data[3360+i*4:3364+i*4]=(positions[i]<<6).to_bytes(4,'little')
  b,bc=run(old/'output.elf',data);n,nc=run(elf,data,True);assert b==n and n[0]==1,label
  directed.append(dict(case=label,geometry_result=n[1],baseline=bc,candidate=nc))
  if exceptions==128:
   bad=data.copy();bad[3364:3368]=bad[3360:3364]
   b,_=run(old/'output.elf',bad);n,_=run(elf,bad);assert b==n and n[0]==1 and n[1]==0,'duplicate exception';directed.append(dict(case='duplicate exception rejected by independent planner'))
   bad=data.copy();bad[2336+127*8+7]=128
   b,_=run(old/'output.elf',bad);n,_=run(elf,bad);assert b==n and n[0]==0,'last object reserved';directed.append(dict(case='last object reserved bit rejected'))
 mutations=[(4385,b'\0\0','zero maps'),(4385,(1057).to_bytes(2,'little'),'map overflow'),(4385,(34).to_bytes(2,'little'),'map row alignment'),(4387,b'\0\0','row count'),(4389,(129).to_bytes(2,'little'),'objects overflow'),(4391,(129).to_bytes(2,'little'),'exception overflow'),(4393,b'\0\0','raster count'),(4395,(33).to_bytes(2,'little'),'palette count'),(4397,b'\3','raw count'),(1,bytes([base[1]|128]),'map reserved bit'),(2343,b'\x80','object reserved bit'),(4320,b'\0','display mask'),(3873,bytes([base[3873]|128]),'raster reserved bit')]
 for at,value,label in mutations:
  data=base.copy();data[at:at+len(value)]=value
  b,_=run(old/'output.elf',data);n,_=run(elf,data);assert b==n and n[0]==0,(label,b[:3],n[:3]);cases.append(label)
 pins={str(p):sha(p) for p in (elf,old/'output.elf',old/'precommit352-3.bin')}
 for frame in range(905,976):
  for suffix in ('expected','records'):
   p=BASE/f'probes/nes-joint278/test07/frame{frame}.{suffix}';pins[str(p)]=sha(p)
 result=dict(passed=True,rows=rows,negative_cases=cases,directed_cases=directed,pins=pins,scope='Preparation only, decoded recorded geometry with existing907 context; not71 full schedules or new source admission proof. Equal RAM object layout required. Poisoned inactive destination tails, exact active input/video/H2 bytes.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(passed=True,frames=len(rows),negative=len(cases),warm=rows[2])))
if __name__=='__main__':main()
