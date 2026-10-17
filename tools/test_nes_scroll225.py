# SPDX-License-Identifier: MIT
"""Selected223 versus225 planner, independent visible-pixel/HDMA oracle.
Actual sink212 packets costed; dual-bank memory modeled. Not physicalFPS.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_scroll225 import ROOT,BASE,sha,once,planner

def host_source():
    s=(ROOT/'tests/nes-functional/resident211_host.c').read_text()
    a=s.index(' for(unsigned i=0;i<2048;i++){');b=s.index(' for(unsigned i=0;i<ref.objects;i++){',a)
    s=s[:a]+''' /* Compare every visible normal pixel using independent SNES map address
  * calculation, not same destination cells. HOFS changes with map rotation. */
 for(unsigned y=0;y<224;y++)if(!((r.raster[y]>>49)&1))for(unsigned x=0;x<256;x++){
  unsigned sx0=(x+ref.hofs[y])&511,sx1=(x+candidate.hofs[y])&511;
  unsigned sy0=(y+ref.vofs[y]+1)&255,sy1=(y+candidate.vofs[y]+1)&255;
  unsigned at0=((sx0/256)*1024+(sy0/8)*32+(sx0/8)%32)*2;
  unsigned at1=((sx1/256)*1024+(sy1/8)*32+(sx1/8)%32)*2;
  unsigned w0=word(ref.map+at0),w1=word(banks[bank].map+at1);
  assert((w0&0xfc00)==(w1&0xfc00));
  const uint8_t *p0=refbg+(w0&1023)*16+(sy0%8)*2;
  const uint8_t *p1=banks[bank].bg+(w1&1023)*16+(sy1%8)*2;
  unsigned c0=((p0[0]>>(7-sx0%8))&1)|(((p0[1]>>(7-sx0%8))&1)<<1);
  unsigned c1=((p1[0]>>(7-sx1%8))&1)|(((p1[1]>>(7-sx1%8))&1)<<1);
  assert(c0==c1);checked++;
 }
'''+s[b:]
    s=once(s,' assert(ref.hdma_size==candidate.hdma_size&&!memcmp(ref.hdma,candidate.hdma,ref.hdma_size));',''' unsigned hy=0,hi=0;
 while(candidate.hdma[hi]){unsigned n=candidate.hdma[hi++];assert(n<128&&hy+n<=224);
  unsigned h=word(candidate.hdma+hi),v=word(candidate.hdma+hi+2);hi+=4;
  for(unsigned k=0;k<n;k++,hy++)assert(h==candidate.hofs[hy]&&v==candidate.vofs[hy]);
 }
 assert(hy==224&&hi+1==candidate.hdma_size);''')
    s=once(s,' assert(!memcmp(ref.hofs,candidate.hofs,sizeof ref.hofs)&&!memcmp(ref.vofs,candidate.vofs,sizeof ref.vofs));',''' assert(!memcmp(ref.vofs,candidate.vofs,sizeof ref.vofs));
 for(unsigned y=0;y<224;y++)assert(candidate.hofs[y]<=511&&(candidate.hofs[y]&7)==ref.hofs[y]);''')
    s=once(s,'static void scrolling(void){','''static void scrolling(void){''')
    s=s.replace('f<96','f<192').replace('synthetic_frames=96','synthetic_frames=192')
    s=once(s,'   r.raster[y]=(UINT64_C(0x1e)<<36)|((uint64_t)(f&7)<<30);','''   unsigned coarse=(f/2)&63;
   r.raster[y]=(UINT64_C(0x1e)<<36)|((uint64_t)(f&7)<<30)|(coarse&31)|((coarse&32)<<5);''')
    s=s.replace('x+f/8','x+f/2')
    # Cost the actual deployed sink against the generated map/metadata. The
    # copy protects the real bank commit/fault assertions in the host oracle.
    s=once(s,'static void verify_bank(void){','''#include "nes_native_sink165.h"
static unsigned packets225,wire225,mapwire225,mapcommands225;
static bool cost_exchange(void *ctx,const uint8_t *p,unsigned n,uint8_t ack[12]){
 (void)ctx;packets225++;wire225+=n+3;
 if(p[1]==2&&(p[0]==2||p[0]==4)){mapwire225+=n+3;mapcommands225++;}
 ack[0]=p[0]==3;ack[1]=p[0];memcpy(ack+2,p+2,8);ack[10]=0x65;ack[11]=0x9a;return true;
}
static void cost225(void){
 struct nes_resident211 c=cache;struct nes_native_sink165 sink;
 nes_sink165_reset(&sink,cost_exchange,NULL);sink.serial=c.serial-1;sink.displayed=c.displayed;
 c.prepared=false;assert(nes_sink212_begin(&sink,&c));c.prepared=true;
 assert(nes_sink212_seal(&sink,&candidate,&c));
}
static void verify_bank(void){''')
    s=once(s,' assert(cache.prepared);verify_bank();',' assert(cache.prepared);verify_bank();cost225();')
    marker='static bool empty_writer('
    extra='''/* Arbitrary coarse placement, two-way wrap, shrink/grow, raw patches,
 * cross-tag rows and epoch changes. Geometry need not agree with raster X:
 * rotation must remain exact regardless, not guess data from scroll delta. */
static void adversarial225(void){
 reset();
 for(unsigned f=0;f<128;f++){
  source(f%8,60000+f);
  for(unsigned y=0;y<224;y++)if(!((r.raster[y]>>49)&1)){
   unsigned c=(f&1)?(63-f-y/8)&63:(f+y)&63;
   r.raster[y]=(r.raster[y]&~UINT64_C(0x41f))|(c&31)|((c&32)<<5);
  }
  run_frame(1+f/32);
 }
}
'''
    s=once(s,marker,extra+marker)
    s=once(s,' compatibility();scrolling();faults();',' compatibility();scrolling();adversarial225();faults();')
    s=once(s,' compatibility();scrolling();adversarial225();faults();',''' compatibility();
 unsigned w=mapwire225,c=mapcommands225,m=mapbytes;scrolling();
 printf("COST225 scroll_map_packet_bytes=%u scroll_map_commands=%u scroll_upload_bytes=%u\\n",mapwire225-w,mapcommands225-c,mapbytes-m);
 adversarial225();faults();
 printf("TOTAL225 packets=%u clocked_E1_bytes=%u map_E1_bytes=%u map_commands=%u\\n",packets225,wire225,mapwire225,mapcommands225);''')
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
    src=BASE/'probes/nes-ingress223/arm01/src';manifest=json.loads((src.parents[1]/'manifest01.json').read_bytes());pins={}
    names=['nes_planner211.c','nes_resident211.c','nes_resident211.h','nes_native165.c','nes_native165.h','nes_native_video165.h','nes_plan191.h','nes_trace166.c','nes_trace166.h','nes_native_sink165.c','nes_native_sink165.h','nes_sink_trace168.c','nes_sink_trace168.h','nes_sink_bulk195.h','nes_sink_bulk195.inc']
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    results={}
    for kind in ['baseline','candidate']:
        out=d/kind;out.mkdir()
        for n in names:
            assert sha(src/n)==manifest['arm01/src/'+n];pins[str((src/n).relative_to(BASE))]=sha(src/n);shutil.copyfile(src/n,out/n)
        for n in ['reference203.c','reference203.h','scene203.inc']:
            old=BASE/'probes/nes-resident211/test04'/n;shutil.copyfile(old,out/n);pins[str(old.relative_to(BASE))]=sha(old)
        (out/'host.c').write_text(host_source(),encoding='utf8',newline='\n')
        if kind=='candidate':
            f=out/'nes_planner211.c';f.write_text(planner(f.read_text()),encoding='utf8',newline='\n')
        files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c']
        for args,log in [([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe'],'build'),([out/'host.exe'],'test')]:
            with (out/(log+'.log')).open('wb') as f:q=subprocess.run(list(map(str,args)),cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
            text=(out/(log+'.log')).read_text(errors='replace');assert q.returncode==0,text[-6000:]
        results[kind]=text;print(kind+' '+text,flush=True)
    report=dict(passed=True,results=results,inputs=pins,public_sources={n:sha(ROOT/n) for n in ['tools/nes_scroll225.py','tools/test_nes_scroll225.py']},scope=__doc__,physical=False,new_fpga=False)
    (d/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
