# SPDX-License-Identifier: MIT
"""Actual full RUN output231: real queue/planner/sink, modeled FPGA/SNES."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_runtime233 import BASE,sha,once


def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);old=BASE/'probes/nes-repeat227/runtime01'
 for n in ['reference203.c','reference203.h']+[f'scene{i}.wire' for i in range(11)]:shutil.copyfile(old/n,d/n)
 for f in (a.arm/'src').iterdir():
  if f.name.startswith('nes_') and f.suffix in ('.c','.h','.inc'):shutil.copyfile(f,d/f.name)
 s=(old/'host213.c').read_text().replace('0x2271','0x2311')
 s=once(s,'static struct nes_resident211 cache;', 'static struct nes_resident211 cache;\nstatic struct nes_dirty231 dirty;static struct nes_source231 source;\nstatic uint8_t meta233[2][3930];')
 s=s.replace('0x5a04eed7u,true)','0x5a04eed7u,true,&dirty,&source)').replace('0x5a04eed7u,false)','0x5a04eed7u,false,&dirty,&source)')
 s=once(s,'u16(p+12)==168','u16(p+12)==222')
 s=once(s,'   assert(!memcmp(oam227[cache.target],video.oam,544));', '''   assert(!memcmp(p+184,dirty.stale[cache.target],54));
   assert(!memcmp(meta233[cache.target],output.cgram,512));
   assert(!memcmp(meta233[cache.target]+512,output.hdma,output.hdma_size));
   if(output.patch_count)for(unsigned j=0;j<2297;j++)assert(meta233[cache.target][512+1121+j]==nes_dirty231_byte(&output,5,j));
   assert(!memcmp(oam227[cache.target],output.oam,544));''')
 s=once(s,'!(at%64)&&!(len%64)','!(at%16)&&!(len%16)')
 s=once(s,'  else assert(p[0]==1||p[1]>=2);', '''  else if(p[1]==3||p[1]==5){
   unsigned at=u16(p+10),len=u16(p+(p[0]==2?12:14)),base=p[1]==3?0:512;
   assert(p[0]==2||p[0]==4||p[0]==5);assert(at+len<=(p[1]==3?512u:3418u));
   for(unsigned j=0;j<len;j++)meta233[cache.target][base+at+j]=p[16+(p[0]==2?j:(j&1))];
  }
  else assert(p[0]==1||p[1]>=2);''')
 s=once(s,'  assert(cache.fault&&!cache.open&&!cache.write&&!cache.ctx);','  assert(cache.fault&&!cache.open&&!cache.write&&!cache.ctx);\n  assert(dirty.fault&&!dirty.open&&!dirty.prepared&&!dirty.valid&&source.fault&&!source.valid);')
 s=once(s,' init();assert(!cache.displayed&&!cache.serial&&!cache.fault);',' init();assert(!cache.displayed&&!cache.serial&&!cache.fault);\n assert(!dirty.fault&&!dirty.valid&&!source.fault&&!source.valid);\n for(unsigned b=0;b<2;b++)for(unsigned i=0;i<54;i++)assert(dirty.stale[b][i]==255);')
 (d/'host.c').write_text(s,encoding='utf-8',newline='\n')
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 files=['host.c','reference203.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_planner211.c','nes_resident211.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','nes_budget210.c','nes_delta231.c']
 for name,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),('run',[d/'host.exe'])]:
  with (d/(name+'.log')).open('wb') as f:q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(d/(name+'.log')).read_text(errors='replace');assert q.returncode==0,text[-4000:]
 assert 'frames=9 ' in text and text.count('PASS METADATA203 fault=')==6
 result=dict(passed=True,scope=__doc__,output=text,files={n:sha(d/n) for n in files},script_sha256=sha(Path(__file__)),ingress_delta=False,actual_snes=False,physical=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(text)


if __name__=='__main__':main()
