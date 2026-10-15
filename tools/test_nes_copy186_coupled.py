# SPDX-License-Identifier: MIT
"""Production sink/window + actual65816 COPY6, compared with full-map transport.

Synthetic legal complex maps isolate inheritance; not a physical FPS measure.
File delivery faults deliberately change a request after the queue CRC check.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_clip178 import replace
from nes_game147 import ROOT,sha

MAIN=r'''
int main(int argc,char **argv){
 assert(argc==3);mode=argv[2];events=fopen("events.txt","w");assert(events);
 assert(nes_window184_init(&window,queued_transfer,queued_guard,NULL,65536));
 nes_sink165_reset(&sink,nes_window184_barrier,&window);sink.enqueue=nes_window184_enqueue;
 assert(scene(argv[1],"rows0-phase0",12,0,0x1e));
 bool ok=scene(argv[1],"rows7-phase0",13,7,0x1e);
 if(strcmp(mode,"reference")&&strcmp(mode,"inherit")){
  assert(!ok&&sink.state==NES_SINK165_FAULT&&queue_fault&&window.error==4&&last_ack[0]>=0xe0);
 }else{
  assert(ok);assert(scene(argv[1],"rows7-phase1",14,7,0x18));
  assert(scene(argv[1],"rows0-phase0",15,0,0x1e));
  assert(scene(argv[1],"rows0-phase0",16,0,0x1e));
  assert(scene(argv[1],"rows1-phase0",17,1,0x1e));
  assert(scene(argv[1],"rows7-phase2",18,7,0x18));
  assert(accepted==retired&&window.sent==window.retired);
 }
 fprintf(events,"E 0 0 0\n");fclose(events);
 FILE *f=fopen("producer-done.txt","w");assert(f);fprintf(f,"PASS\n");fclose(f);
 printf("PASS COPY186 COUPLED %s accepted=%u retired=%u max_used=%u error=%u\n",mode,accepted,retired,max_used,window.error);return 0;
}
'''

def main():
 p=argparse.ArgumentParser()
 for n in ['out','candidate','prior','fixtures','gcc','mesen']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--modes',nargs='+',default=['reference','inherit','badbase','badalign','badsize','badsection','badexpanded','badtoken','stop_inherit'])
 p.add_argument('--reference',type=Path,help='Earlier complete reference pixels for a follow-up case')
 a=p.parse_args()
 for n in vars(a):
  if isinstance(getattr(a,n),Path):setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False);pins={}
 for f in a.candidate.glob('nes_*'):
  if f.is_file():shutil.copyfile(f,a.out/f.name);pins[f.name]=sha(f)
 shutil.copytree(a.candidate/'client',a.out/'client')
 host=(a.prior/'host.c').read_text();start=host.index('static bool exchange(');end=host.index('static unsigned read_file(',start)
 host=host[:start]+(ROOT/'tests/nes-functional/window184_filebus.inc').read_text()+'\n'+host[end:]
 host=host[:host.index('int main(')]+MAIN
 host=replace(host,' memset(&p,0,sizeof(p));',' uint8_t oldmap[4096];memcpy(oldmap,p.map,4096);unsigned base=p.generation;\n memset(&p,0,sizeof(p));')
 host=replace(host,'assert(layout==sizeof(p));','assert(layout==15888);')
 host=replace(host,' assert(read_file(dir,"cgram.bin",p.cgram,sizeof(p.cgram))==512);',r'''
 /* Every slot refers to loaded BG1; palette/flip variation defeats RLE.
  * Gen14 changes one64-byte block, gen15 all blocks, then normal/raw reuse. */
 for(unsigned i=0;i<2048;i++){
  unsigned v=1|0x2000|(((i*13+i/7+(gen>=15?1:0))&3)<<10)|((i%3)<<14);
  if(gen==14&&i>=32&&i<64)v^=0x400;
  p.map[i*2]=(uint8_t)v;p.map[i*2+1]=(uint8_t)(v>>8);
 }
 p.map_inherit=gen>12&&strcmp(mode,"reference");p.map_base_generation=(uint16_t)base;p.map_dirty=0;
 for(unsigned b=0;b<64;b++)if(memcmp(oldmap+b*64,p.map+b*64,64))p.map_dirty|=UINT64_C(1)<<b;
 assert(read_file(dir,"cgram.bin",p.cgram,sizeof(p.cgram))==512);''')
 (a.out/'host.c').write_text(host,encoding='utf8',newline='\n')
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'gcc.log').open('wb') as f:r=subprocess.run([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2','host.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','-o','host.exe'],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(a.out/'gcc.log').read_text(errors='replace')
 lua=(a.prior/'normal/capture.lua').read_text().split('\n',2)[2]
 lua=replace(lua,'if not packet then local f=','if not packet and not rejected then local f=')
 lua=replace(lua,'pb(0)==4 or pb(0)==5)','pb(0)==4 or pb(0)==5 or pb(0)==6)')
 lua=replace(lua,'local expected=pb(16+(pb(0)>=4 and (i%2) or i))',"local expected=pb(0)==6 and rd((base~0x8000)+i) or pb(16+(pb(0)>=4 and (i%2) or i))")
 start=lua.index('assert(commits==');end=lua.index('\n',start)
 lua=lua[:start]+"assert(commits==((MODE=='reference' or MODE=='inherit') and 7 or 1))"+lua[end:]
 lua=replace(lua,"packet=f:read('*a');f:close()end end",r'''packet=f:read('*a');f:close()
 if packet:byte(1)==6 and pw(8)==13 then
  local b={packet:byte(1,#packet)}
  if MODE=='badbase' then b[17]=b[17]~1 end
  if MODE=='badalign' then b[11]=64 end
  if MODE=='badsize' then b[13]=1;b[#b]=nil end
  if MODE=='badsection' then b[2]=3 end
  if MODE=='badexpanded' then b[15]=64;b[16]=0 end
  if MODE=='badtoken' then b[3]=b[3]~1 end
  packet=string.char(table.unpack(b))
 end
 end end''')
 lua=replace(lua,'if a==0x6001 then',"if a==0x6001 then\n  if MODE=='stop_inherit' and packet and pb(0)==3 and pw(8)==13 and chunks>0 then return 128 end")
 cases=[]
 for mode in a.modes:
  d=a.out/mode;d.mkdir();(d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+lua,encoding='utf8')
  with (d/'host.log').open('wb') as hf,(d/'mesen.log').open('wb') as mf:
   h=subprocess.Popen([str(a.out/'host.exe'),str(a.fixtures),mode],cwd=d,env=env,stdout=hf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/sink165.sfc'),'--timeout=70','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=80);hr=h.wait(timeout=5)
   finally:
    for child in [h,m]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==hr==0,((d/'mesen.log').read_text(errors='replace')[-2000:],(d/'host.log').read_text(errors='replace')[-1000:])
  reference=a.reference or a.out/'reference'
  if mode=='inherit':
   for i in range(1,8):assert (d/f'frame-{i}.rgb').read_bytes()==(reference/f'frame-{i}.rgb').read_bytes(),i
  elif mode!='reference':assert (d/'frame-1.rgb').read_bytes()==(reference/'frame-1.rgb').read_bytes()
  packets=[f.read_bytes() for f in sorted(d.glob('req-*.bin'))];copy=[b for b in packets if b[0]==6]
  assert bool(copy)==(mode!='reference'),(mode,len(copy))
  c=json.loads((d/'consumer-result.json').read_bytes());c.update(mode=mode,copies=len(copy),map_packets=sum(b[1]==2 for b in packets),map_wire=sum(len(b) for b in packets if b[1]==2));cases.append(c);print(json.dumps(c),flush=True)
 result=dict(passed=True,cases=cases,pins=pins,scope=__doc__,snes_rom=sha(a.out/'client/sink165.sfc'),generator=sha(Path(__file__)),physical=False,fps60=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
