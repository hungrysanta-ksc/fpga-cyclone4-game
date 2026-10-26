# SPDX-License-Identifier: MIT
"""Exercise BG misses/kind checks and per-call lifetime on the actual M4 ELF."""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,ELFFile
from check_nes_compact354 import objects
from nes_delta231 import sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True)
 p.add_argument('--reference',type=Path,required=True);p.add_argument('--snapshots',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 images=(a.reference/'output.elf',a.candidate/'output.elf');syms=objects(images[0]);assert syms==objects(images[1])
 # Native ARM layout: verified against the compiled header offsets in the
 # private layout370.o fixture, not inferred from host pointer sizes.
 TILE=5728;NTILES=9854;GEN=9824;COUNTS=9826;STATE=9860
 layout=a.candidate/'layout370.o'
 with layout.open('rb') as f:
  e=ELFFile(f);symbol=e.get_section_by_name('.symtab').get_symbol_by_name('layout370')[0]
  blob=e.get_section(symbol['st_shndx']).data()[symbol['st_value']:symbol['st_value']+symbol['st_size']]
  assert struct.unpack('<6I',blob)==(TILE,NTILES,GEN,COUNTS,STATE,syms['input285'][1])
 rows=[];pins={str(p):sha(p) for p in (*images,layout,a.candidate/'layout370.c',Path(__file__))}
 def u16(b,i):return int.from_bytes(b[i:i+2],'little')
 def state(arm):return {n:bytes(arm.uc.mem_read(at,size)) for n,(at,size) in syms.items()}
 for index in (0,1,5,14,23):
  f=a.snapshots/f'row369-{index}.bin';data=f.read_bytes();pins[str(f)]=sha(f)
  for case in ('BG kind absent','BG tag absent','wrong generation','STOP','stack cache must expire','alternate kind absent','cycle3','cycle4','cycle8'):
   results=[]
   for image in images:
    arm=ARM(image,None);arm.uc.mem_write(0x20000000,data);s=arm.symbols['input285']
    initial=state(arm)
    if case=='stack cache must expire':
     assert arm.call('next_step286',[])==1
     # Restore only existing globals. Keep the previous call's stack bytes
     # so the second call cannot accidentally reuse uninitialized cache data.
     for name,b in initial.items():arm.uc.mem_write(syms[name][0],b)
    source=bytearray(arm.uc.mem_read(s,syms['input285'][1]));count=u16(source,NTILES)
    ctx=bytes(arm.uc.mem_read(arm.symbols['ctx286'],124));g=ctx[117];first=ctx[20+g]
    group=source[2112+first]>>3;tag=u16(source,group*66)&8191
    at=next(i for i in range(count) if u16(source,TILE+i*4)==tag)
    if case in ('BG kind absent','stack cache must expire'):source[TILE+at*4+2]=2
    elif case=='BG tag absent':
     source[TILE+at*4:TILE+(count-1)*4]=source[TILE+(at+1)*4:TILE+count*4]
     source[NTILES:NTILES+2]=(count-1).to_bytes(2,'little')
    elif case=='wrong generation':source[GEN:GEN+2]=(u16(source,GEN)^128).to_bytes(2,'little')
    elif case=='alternate kind absent':
     # Column2 has an alternate tag absent from the BG kind set. Original
     # and candidate must both reject it even after ordinary positive hits.
     alt=next(u16(source,TILE+i*4) for i in range(count) if u16(source,TILE+i*4)!=tag)
     j=next(i for i in range(count) if u16(source,TILE+i*4)==alt);source[TILE+j*4+2]=2
     source[COUNTS+6:COUNTS+8]=(1).to_bytes(2,'little')
     source[5216:5220]=((alt<<19)|((first*33+2)<<6)).to_bytes(4,'little')
    elif case.startswith('cycle'):
     n=int(case[5:]);tags=[u16(source,TILE+i*4) for i in range(count) if source[TILE+i*4+2]&1][:n]
     assert len(tags)==n
     for x in range(33):
      at=group*66+x*2;source[at:at+2]=((u16(source,at)&0x6000)|tags[x%n]).to_bytes(2,'little')
    arm.uc.mem_write(s,bytes(source))
    if case=='STOP':arm.call('stop286',[])
    ok=arm.call('next_step286',[]);assert ok==(1 if case.startswith('cycle') else 0),(index,case,'unexpected admission')
    results.append((ok,state(arm)))
   assert results[0]==results[1],(index,case,'state mismatch')
   rows.append(dict(snapshot=index,case=case,result=results[0][0],exact_state=True))
 result=dict(passed=True,new_timing=False,rows=rows,pins=pins)
 assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps(dict(passed=True,cases=len(rows))))
if __name__=='__main__':main()
