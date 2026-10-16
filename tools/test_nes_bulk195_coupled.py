# SPDX-License-Identifier: MIT
"""Production C op7/barrier -> actual65816 DMA/VRAM/finalACK, held file bus.
Synthetic186 scene tiles replace FPGA producer; not RTL coupling or game FPS.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
from nes_bulk195 import ROOT,prepare
from nes_clip178 import replace
from test_nes_bulk194_snes import script
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

STAGE=r'''
#include "nes_sink_bulk195.h"
static uint32_t chunk_token=0x19400000;
static bool bulk(unsigned kind,unsigned slot,const uint8_t *b,unsigned n){
 unsigned unit=kind?32:16;uint8_t d[12]={1,(uint8_t)kind,(uint8_t)n,(uint8_t)(n>>8),
  (uint8_t)(slot*unit),(uint8_t)(slot*unit>>8),(uint8_t)sink.generation,(uint8_t)(sink.generation>>8)};
 for(unsigned i=0;i<4;i++)d[8+i]=(uint8_t)(chunk_token>>(8*i));
 chunk_token++;
 /* Test fixture only: production FPGA193 owns these bytes. Publish the tile
  * before allowing real C to publish op7, never inject WRAM/PPU/ACK values. */
 char path[80];snprintf(path,sizeof(path),"tile-%04u.bin",accepted+1);
 FILE *f=fopen(path,"wb");assert(f&&fwrite(b,1,n,f)==n);fclose(f);
 unsigned before=kind?sink.obj_next:sink.bg_next;
 bool ok=nes_sink195_bulk(&sink,d);
 if(!ok)assert((kind?sink.obj_next:sink.bg_next)==before);
 return ok;
}
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
 p.add_argument('--modes',nargs='+',default=['normal','bad_token','stop_dma']);a=p.parse_args()
 a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 base=ROOT.parent;old=base/'probes/nes-copy186';ref=old/'evidence/coupled03/inherit'
 candidate=a.out/'candidate';prepare(old/'build01',candidate)
 for f in candidate.iterdir():
  if f.is_file():shutil.copyfile(f,a.out/f.name)
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
 mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
 fixtures=base/'probes/nes-consume181/evidence/test05'
 host=(old/'evidence/coupled03/host.c').read_text()
 host=replace(host,'static unsigned read_file(',STAGE+'\nstatic unsigned read_file(')
 host=replace(host,' for(unsigned i=0;i<bg;){unsigned n=bg-i;if(n>15)n=15;assert(nes_sink165_pattern(&sink,0,i,pattern+i*16,n*16));i+=n;}',
 ''' if(gen==12){memset(pattern+bg*16,0,4096-bg*16);bg=256;p.bg_count=256;}
 for(unsigned i=0;i<bg;){unsigned n=bg-i;if(n>128)n=128;if(!bulk(0,i,pattern+i*16,n*16))return false;i+=n;}''')
 host=replace(host,' for(unsigned i=0;i<obj;){unsigned n=obj-i;if(n>7)n=7;assert(nes_sink165_pattern(&sink,1,i,pattern+i*32,n*32));i+=n;}',
 ' for(unsigned i=0;i<obj;){unsigned n=obj-i;if(n>64)n=64;if(!bulk(1,i,pattern+i*32,n*32))return false;i+=n;}')
 host=replace(host,'if(strcmp(mode,"reference")&&strcmp(mode,"inherit"))','if(strcmp(mode,"normal"))')
 (a.out/'host.c').write_text(host,encoding='utf8',newline='\n')
 shutil.copyfile(ROOT/'tests/nes-functional/bulk195_host.c',a.out/'unit.c')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 def run(args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(a.out/(label+'.log')).read_text(errors='replace')[-4000:]
 for name,extra in [('unit',[]),('host',['nes_sink_window184.c'])]:
  run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',name+'.c','nes_native_sink165.c','nes_sink_trace168.c',*extra,'-o',name+'.exe'],'gcc-'+name)
 run([a.out/'unit.exe'],'unit')
 lua=replace(script(ref),' if not packet and (rejected or ordinal>TOTAL) then',
             " local done=io.open(OUT_DIR..'/producer-done.txt','r')\n if done then done:close();")
 cases=[]
 for mode in a.modes:
  d=a.out/mode;d.mkdir();(d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+lua,encoding='utf8')
  with (d/'host.log').open('wb') as hf,(d/'mesen.log').open('wb') as mf:
   h=subprocess.Popen([str(a.out/'host.exe'),str(fixtures),mode],cwd=d,env=env,stdout=hf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(mesen),'--testRunner',str(d/'capture.lua'),str(candidate/'client/sink165.sfc'),'--timeout=70','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=80);hr=h.wait(timeout=5)
   finally:
    for child in (h,m):
     if child.poll() is None:child.kill();child.wait()
  assert mr==hr==0,((d/'mesen.log').read_text(errors='replace')[-3000:],(d/'host.log').read_text(errors='replace')[-2000:])
  for i in range(1,8 if mode=='normal' else 2):assert (d/f'frame-{i}.rgb').read_bytes()==(ref/f'frame-{i}.rgb').read_bytes(),(mode,i)
  c=json.loads((d/'consumer-result.json').read_bytes());c['mode']=mode;cases.append(c);print(json.dumps(c),flush=True)
 pins={str(p.relative_to(base)).replace('\\','/'):sha(p) for p in (old/'evidence/coupled03/host.c',ref/'capture.lua',ROOT/'tools/test_nes_bulk194_snes.py',ROOT/'tools/nes_bulk195.py',Path(__file__),ROOT/'src/nes/firmware/nes_sink_bulk195.inc',ROOT/'src/nes/firmware/nes_sink_bulk195.h',ROOT/'tests/nes-functional/bulk195_host.c')}
 result=dict(passed=True,cases=cases,unit=(a.out/'unit.log').read_text().strip(),source_pins=pins,
  fixture_pins={str(p.relative_to(fixtures)).replace('\\','/'):sha(p) for p in fixtures.rglob('*') if p.is_file()},
  client_sha256=sha(candidate/'client/sink165.sfc'),compiler_sha256=sha(gcc),mesen_sha256=sha(mesen),
  scope=__doc__,production_c_issuer=True,production_descriptor_acquisition=False,rtl_cosimulation=False,actual_scroll=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
