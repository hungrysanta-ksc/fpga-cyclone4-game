# SPDX-License-Identifier: MIT
"""Existing adversarial converter scenes with actual231 sparse C packets.

Independent byte consumer below is a host model, not actual65816 code.
"""
from pathlib import Path
import argparse,json,os,subprocess
from nes_delta231 import materialize,sha,once,BASE

CONSUMER=r'''
static uint8_t meta231[2][8570],coverage231[8570];
static unsigned consumer_frames;
static const unsigned offsets231[4]={0,4096,4608,5152};
static const unsigned sizes231[4]={4096,512,544,3418};
static void consume231(const uint8_t *p,unsigned n){
 unsigned op=p[0],k=p[1],at=word(p+10),len=word(p+12),expanded=word(p+14);
 assert(n==len+16);unsigned bank=cache.target;
 if(op==1){assert(len==12&&word(p+16)==0x2311&&word(p+18)==bank);memset(coverage231,0,sizeof coverage231);return;}
 if(op==3){
  assert(len==222&&word(p+36)==0x2311);
  const uint8_t *bits=p+16+168;
  for(unsigned bit=0;bit<432;bit++)if(bits[bit/8]&(1u<<(bit%8))){
   unsigned a,count=16;
   if(bit<256)a=bit*16;
   else if(bit<288)a=4096+(bit-256)*16;
   else{if(!candidate.patch_count)continue;a=5152+1121+(bit-288)*16;if(bit==431)count=9;}
   for(unsigned i=0;i<count;i++)assert(coverage231[a+i]);
  }
  assert(!memcmp(meta231[bank],candidate.map,4096));
  assert(!memcmp(meta231[bank]+4096,candidate.cgram,512));
  assert(!memcmp(meta231[bank]+4608,candidate.oam,544));
  assert(!memcmp(meta231[bank]+5152,candidate.hdma,candidate.hdma_size));
  if(candidate.patch_count){
   for(unsigned i=candidate.hdma_size;i<1121;i++)assert(meta231[bank][5152+i]==0);
   for(unsigned i=0;i<2297;i++)assert(meta231[bank][5152+1121+i]==nes_dirty231_byte(&candidate,5,i));
  }
  consumer_frames++;return;
 }
 assert(k>=2&&k<=5);unsigned count=op==2?len:expanded;
 assert((op==2&&!expanded)||(op==4&&len==2)||(op==5&&len==2)||(op==8&&len==4&&k==4));
 assert(count&&at+count<=sizes231[k-2]);
 for(unsigned i=0;i<count;i++){unsigned dst=offsets231[k-2]+at+i;meta231[bank][dst]=p[16+(op==2?i:i%len)];coverage231[dst]=1;}
}
'''

FAULTS=r'''
static void dirty_faults231(void){
 unsigned cases=0;
 for(unsigned which=0;which<5;which++){
  reset();source(0,1);run_frame(1);source(0,2);convert_input();
  assert(nes_resident211_begin(&cache,1,true,2,write_slot,NULL));
  assert(nes_native_video231_plan(&input,lut,&candidate,&cache,&dirty));
  assert(!nes_dirty231_commit(&dirty,dirty.serial+(which==0),dirty.generation+(which==1),which==2?1-dirty.target:dirty.target,which!=3&&which!=4));
  assert(dirty.fault&&!dirty.valid&&!dirty.open);assert(!nes_dirty231_begin(&dirty,&cache));cases++;
 }
 /* A changed block must propagate to the other destination even when it
  * returns to the last-displayed value before that bank is reused. */
 reset();for(unsigned i=0;i<8;i++){source(i==2?2:0,100+i);run_frame(1);}
 printf("DIRTY231 faults=%u alternate_base=PASS\n",cases);
}
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();pins=materialize(d)
    baseline=BASE/'probes/nes-scroll225/test02/candidate/host.c';s=baseline.read_text()
    s=once(s,'#include "nes_resident211.h"','#include "nes_delta231.h"\nstatic struct nes_dirty231 dirty;')
    s=s.replace('nes_native_video211_plan(&input,lut,&candidate,&cache)','nes_native_video231_plan(&input,lut,&candidate,&cache,&dirty)')
    at=s.index('static bool cost_exchange');s=s[:at]+CONSUMER+s[at:]
    s=once(s,'(void)ctx;packets225++;wire225+=n+3;','(void)ctx;consume231(p,n);packets225++;wire225+=n+3;')
    s=once(s,'struct nes_resident211 c=cache;struct nes_native_sink165 sink;','struct nes_resident211 c=cache;struct nes_dirty231 dc=dirty;struct nes_native_sink165 sink;')
    s=once(s,'nes_sink212_seal(&sink,&candidate,&c)','nes_sink231_seal(&sink,&candidate,&c,&dc)')
    s=once(s,'assert(nes_resident211_commit(&cache,cache.serial,r.generation,cache.target,true));','assert(nes_resident211_commit(&cache,cache.serial,r.generation,cache.target,true));assert(nes_dirty231_commit(&dirty,cache.serial,r.generation,cache.target,true));')
    s=once(s,'nes_resident211_reset(&cache);','nes_resident211_reset(&cache);nes_dirty231_reset(&dirty);memset(meta231,0xa5,sizeof meta231);')
    pos=s.index('int main(');s=s[:pos]+FAULTS+s[pos:]
    s=once(s,'adversarial225();faults();','adversarial225();faults();dirty_faults231();printf("CONSUMER231 frames=%u metadata_exact=1\\n",consumer_frames);')
    (d/'host.c').write_text(s,encoding='utf-8',newline='\n')
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
    for label,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),('run',[d/'host.exe'])]:
        with (d/(label+'.log')).open('wb') as log:q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0,text[-6000:]
    result=dict(passed=True,scope=__doc__,pins=pins,script_sha256=sha(Path(__file__)),host_sha256=sha(d/'host.c'),baseline_host_sha256=sha(baseline),output=text)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(text)


if __name__=='__main__':main()
