# SPDX-License-Identifier: MIT
"""Private PC C sender for complete mask8 replay; not ARM state allocation."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_delta231 import BASE,sha,once

HELPER=r'''
/* PC oracle storage, not proposed ARM allocation. The product must use the
 * existing previous-map lifetime; this fixture keeps an independent copy. */
static uint8_t maplast247[4096],mapstale247[2][256];static bool mapstarted247;
static bool map247(struct nes_native_sink165 *s,const struct nes_native_video165 *p,unsigned bank){
 if(!mapstarted247){memset(mapstale247,255,sizeof mapstale247);mapstarted247=true;}
 for(unsigned w=0;w<2048;w++)if(memcmp(p->map+2*w,maplast247+2*w,2)){
  mapstale247[0][w/8]|=(uint8_t)(1u<<(w%8));mapstale247[1][w/8]|=(uint8_t)(1u<<(w%8));
 }
 uint8_t b[240]={2};unsigned used=1;
 for(unsigned g=0;g<256;g++){
  unsigned mask=mapstale247[bank][g];if(!mask)continue;
  unsigned n=2;for(unsigned bit=0;bit<8;bit++)if(mask&(1u<<bit))n+=2;
  if(used+n>240){if(!packet(s,9,2,0,b,used))return false;used=1;}
  b[used++]=(uint8_t)g;b[used++]=(uint8_t)mask;
  for(unsigned bit=0;bit<8;bit++)if(mask&(1u<<bit)){
   memcpy(b+used,p->map+g*16+bit*2,2);used+=2;
  }
 }
 return used==1||packet(s,9,2,0,b,used);
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-wholepath247/coalesce-host01';pins={}
 for f in old.iterdir():
  if f.suffix in ('.c','.h','.inc'):
   shutil.copyfile(f,out/f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 f=out/'nes_native_sink165.c';s=f.read_text();s=s.replace('0x2311','0x2471')
 s=once(s,'static bool dirty_span231(',HELPER+'\nstatic bool dirty_span231(')
 s=once(s,'!dirty_span231(s,p,d,2,0,4096,0)','!map247(s,p,r->target)')
 s=once(s,' uint8_t descriptor[222];', ''' if(!packet(s,10,2,0,mapstale247[r->target],240)||!packet(s,10,2,240,mapstale247[r->target]+240,16))return false;
 uint8_t descriptor[190];''')
 s=once(s,'memcpy(descriptor+168,d->stale[d->target],54);','memcpy(descriptor+168,d->stale[d->target]+32,22);')
 s=once(s,' if(!nes_resident211_commit(', ' memcpy(maplast247,p->map,4096);memset(mapstale247[r->target],0,256);\n if(!nes_resident211_commit(')
 f.write_text(s,encoding='utf-8',newline='\n')
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
 with (out/'build.log').open('wb') as log:
  done=subprocess.run([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe'],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert done.returncode==0,(out/'build.log').read_text(errors='replace')
 result=dict(passed=True,scope=__doc__,full_arm=False,product_changed=False,input_hashes=pins,output_hashes={f.name:sha(f) for f in out.iterdir() if f.is_file()},script_sha256=sha(Path(__file__)))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copyfile(__file__,out/'prepare.py');print('PASS private mask8 sender compiled')

if __name__=='__main__':main()
