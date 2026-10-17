# SPDX-License-Identifier: MIT
"""Production RUN/200 batching/184 queue integration; SPI peer is a model.
Replay real203 ingress traces; reference planar bytes checked after sparse
descriptor drains. Actual65816 behavior is independently pinned by212/test09.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_runtime213 import ROOT,BASE,sha,once

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 prior=BASE/'probes/nes-metadata203/test04';pins={}
 for name in ['host203.c','reference203.c','reference203.h']+[f'scene{i}.wire' for i in range(11)]:
  f=prior/name;shutil.copyfile(f,a.out/name);pins[str(f.relative_to(BASE))]=sha(f)
 for f in (a.arm/'src').iterdir():
  if f.name.startswith('nes_') and f.suffix in ('.c','.h','.inc'):shutil.copyfile(f,a.out/f.name)
 s=(a.out/'host203.c').read_text()
 s=once(s,'t*31+b*13+variant','t*31+b*13') # immutable physical ROM across geometry
 s=once(s,'static struct nes_native_runtime165 runtime;', '''static struct nes_native_runtime165 runtime;
static struct nes_resident211 cache;
static struct {uint8_t bg[16384],obj[4096],map[4096];} banks[2];
static unsigned checked;
static void verify_bank(void);''')
 s=once(s,'  assert(slot*unit+unit<=sizes[kind==1]);assert(!memcmp(out,(kind==1?obj:bg)+slot*unit,unit));used++;',
            '  assert(slot<(kind==1?128u:1024u));used++;')
 s=once(s,'if(p[0]==7){assert(used&&!memcmp(p+16,descriptors[head]+8,4));used--;head++;bulk_count++;}', '''if(p[0]==7){assert(used&&!memcmp(p+16,descriptors[head]+8,4));
   assert(cache.open&&!cache.displayed?cache.target==0:cache.target!=cache.active);
   unsigned kind=descriptors[head][1],at=u16(descriptors[head]+4),len=u16(descriptors[head]+2);
   memcpy((kind?banks[cache.target].obj:banks[cache.target].bg)+at,pixels[head],len);
   used--;head++;bulk_count++;
  }''')
 s=once(s,'else if(p[0]==3){assert(ended&&!used&&runtime.plan.finished);final_acks++;}', '''else if(p[0]==3){assert(ended&&!used&&runtime.plan.finished&&cache.open&&cache.prepared);
   assert(u16(p+12)==168&&u16(p+16+20)==0x2121&&!memcmp(p+16+24,cache.used,144));
   verify_bank();final_acks++;
  }else if(p[0]==1){assert(u16(p+12)==12&&u16(p+16)==0x2121&&u16(p+18)==cache.target);
   assert(cache.epoch==0x5a04eed7u&&cache.open);
  }else if((p[0]==2||p[0]==4)&&p[1]==2){unsigned at=u16(p+10),len=u16(p+(p[0]==4?14:12));
   assert(!(at%64)&&!(len%64)&&len&&at+len<=4096);
   for(unsigned j=0;j<len;j++)banks[cache.target].map[at+j]=p[16+(p[0]==4?(j&1):j)];
  }''')
 s=once(s,'  retiring=true;retire_delay=3;', '''  assert(cache.displayed&&!cache.open&&!cache.prepared&&cache.active==((runtime.sink.serial-1)&1));
  retiring=true;retire_delay=3;''')
 s=once(s,'NULL,1000000)', 'NULL,1000000,&cache,0x5a04eed7u,true)')
 s=once(s,' token=65530;', ' memset(banks,0xa5,sizeof banks);\n token=65530;')
 s=once(s,'&ref,runtime.sink.displayed,stage,NULL)', '&ref,false,stage,NULL)')
 s=once(s,'  assert(!memcmp(&ref,&output,sizeof ref));', '''  assert(cache.displayed&&!cache.open&&!cache.fault&&cache.active==(i&1));
  printf("FRAME213 gen=%u writes=%u hits=%u map=%08x%08x\\n",r.generation,(unsigned)cache.writes,(unsigned)cache.hits,(unsigned)(cache.map_upload>>32),(unsigned)cache.map_upload);
  if(i==8)assert(cache.hits&&cache.writes==1);''')
 s=once(s,'  printf("PASS METADATA203 fault=', '  assert(cache.fault&&!cache.open&&!cache.write&&!cache.ctx);\n  printf("PASS METADATA203 fault=')
 verify=(ROOT/'tests/nes-functional/resident211_host.c').read_text()
 verify=verify[verify.index('static void verify_bank(void){'):verify.index('static void run_frame(')]
 start=verify.index(' for(unsigned g=0;g<64;g++)');end=verify.index(' assert(!memcmp(banks[bank].map',start)
 verify=verify[:start]+verify[end:]
 verify=verify.replace('candidate','output').replace('refbg','bg').replace('refobj','obj').replace('word(', 'u16(')
 s=s[:s.index('static void init(void){')]+verify+s[s.index('static void init(void){'):]
 s=once(s,' faults();return 0;', ''' faults();
 /* No mutable source admission. Fresh physical-reset premise reinitializes
  * all resident banks, even for the same ROM identity. */
 unsigned before=wire_calls;
 assert(!nes_runtime165_begin(&runtime,&received,&output,lut,transfer,ticks,guard,NULL,1000,&cache,0x5a04eed7u,false));
 assert(runtime.result==NES_RUNTIME165_ARGUMENT&&wire_calls==before);
 init();assert(!cache.displayed&&!cache.serial&&!cache.fault);
 for(unsigned b=0;b<2;b++)for(unsigned i=0;i<144;i++)assert(!cache.resident[b][i]);
 printf("PASS RUNTIME213 reference_bytes=%u mutable_reject=1 cold_restart=1\\n",checked);
 return 0;''')
 (a.out/'host213.c').write_text(s,encoding='utf8',newline='\n')
 sources=['host213.c','reference203.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_planner211.c','nes_resident211.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','nes_budget210.c']
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as log:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,text[-6000:];return text
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*sources,'-o','host.exe'],'build')
 text=run([a.out/'host.exe'],'run');assert 'frames=9 ' in text and text.count('PASS METADATA203 fault=')==6 and 'PASS RUNTIME213' in text
 r=dict(passed=True,output=text,inputs=pins,source_hashes={n:sha(a.out/n) for n in sources},physical=False,rtl_peer='model, not cosimulation',snes_peer='ACK model; independent actual212 evidence reused')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(text)
if __name__=='__main__':main()
