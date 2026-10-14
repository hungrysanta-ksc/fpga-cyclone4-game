# SPDX-License-Identifier: MIT
"""Actual65816/C mailbox: E2/E3 large update, return to delta/noop, mid-copy STOP."""
from pathlib import Path
import argparse,json,subprocess,os,shutil,types
from nes_game147 import ROOT,sha
from nes_banked169 import build
from nes_sink_trace168 import sink_source
import build_nes_sink165 as old

def main():
 p=argparse.ArgumentParser()
 for n in ['out','gcc','mesen','video']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--stop-only',action='store_true')
 a=p.parse_args()
 for n in ['out','gcc','mesen','video']:setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False);assert a.out.as_posix().isascii()
 sources=['tools/nes_banked169.py','tools/test_nes_banked169.py','tools/build_nes_sink165.py','tools/nes_native_local165.py','snes/video_probe/capture_native_sink165.lua','tests/nes-functional/native_sink165_host.c']+['src/nes/firmware/'+n for n in ['nes_native_sink165.c','nes_native_sink165.h','nes_native_video165.h','nes_native165.h','nes_sink_trace168.c','nes_sink_trace168.h']]
 for n in sources:shutil.copyfile(ROOT/n,a.out/Path(n).name)
 f=a.out/'nes_native_sink165.c';f.write_text(sink_source(f.read_text()),encoding='utf8',newline='\n')
 s=(a.out/'native_sink165_host.c').read_text();s='#include "nes_sink_trace168.h"\n'+s
 anchor=' bool ok=nes_sink165_seal(&s,&p,5000);'
 s=s.replace(anchor,''' if(gen==17){
  if(!strcmp(mode,"overflow")){for(unsigned i=0;i<34;i++)p.map[64*i+1]^=0x20;}
  else {for(unsigned i=1;i<4096;i+=2)p.map[i]^=0x20;for(unsigned i=0;i<512;i++)p.cgram[i]^=0x11;for(unsigned i=0;i<128;i++)p.oam[i*4]^=1;}
 }
 bool ok=nes_sink165_seal(&s,&p,5000);
 if(!strcmp(mode,"stop")&&gen==17){assert(!ok&&nes_sink_trace168.ack[0]==0xe4);return;}
''')
 s=s.replace('scene(argv[2],16); /* true zero-delta commit, rotated candidate */','scene(argv[2],16);scene(argv[2],17);if(strcmp(mode,"stop")){scene(argv[2],18);scene(argv[2],19);}')
 s=s.replace(' if(!strcmp(mode,"stop")&&gen==15){assert(!ok&&s.state==NES_SINK165_FAULT&&s.displayed);return;}','')
 start=s.index('  assert(nes_sink165_begin(&s,17));');end=s.index('\n }\n FILE *f=fopen("producer-done',start)
 s=s[:start]+s[end:];s=s.replace('if(strcmp(mode,"stop")){','if(1){',1)
 (a.out/'producer169.c').write_text(s,encoding='utf8',newline='\n')
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'build.log').open('wb') as f:q=subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I','.','producer169.c','nes_native_sink165.c','nes_sink_trace168.c','-o','producer.exe'],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(a.out/'build.log').read_text()
 client=build(a.out/'client')
 # Independent old-layout oracle: each candidate is a first full forced-blank upload.
 src=Path(old.__file__).read_text().replace("call(c,'local165_entry');lda(0x1236)","c.emit(0xe2,0x20);c.store(0x2100,128);c.store(0x1024,0);c.emit(0xc2,0x20);call(c,'local165_entry');lda(0x1236)")
 mod=types.ModuleType('reference169');exec(compile(src,'reference169','exec'),mod.__dict__);mod.build(a.out/'reference')
 results=[]
 for mode,reference in ([('stop',False)] if a.stop_only else [('overflow',True),('budget',True),('overflow',False),('budget',False),('stop',False)]):
  d=a.out/(mode+('-reference' if reference else ''));d.mkdir()
  lua=(ROOT/'snes/video_probe/capture_native_sink165.lua').read_text()
  lua=lua.replace("local revealed=false","local revealed=false\nlocal previousScreen=nil\nlocal oldframes=0\nlocal copied=0")
  lua=lua.replace("return MODE=='stop' and packet and packetbyte(0)==3 and packetword(8)==15 and rd(0x1025)==1 and 128 or 0","return MODE=='stop' and packet and packetbyte(0)==3 and packetword(8)==17 and copied>0 and 128 or 0")
  lua=lua.replace("if a==0x2100 then if revealed then assert(v==15,'post-reveal blank')end;if v==15 then revealed=true end end", "if a==0x2100 then if revealed and not REFERENCE then assert(v==15,'post-reveal blank')end;if v==15 then revealed=true end end\n if a==0x420b and packet and packetbyte(0)==3 and (rd(0x1025)==0xe2 or rd(0x1025)==0xe3) then copied=copied+1 end")
  lua=lua.replace("if revealed and (a==0x2118", "if not REFERENCE and revealed and (a==0x2118")
  lua=lua.replace("assert(captured==(MODE=='stop' and 1 or 3))","assert(captured==(MODE=='stop' and 3 or 6));if not REFERENCE then assert(copied>0,'fallback not exercised')end")
  lua=lua.replace('"spc":%d}', '"spc":%d,"fallback_chunks":%d,"old_frames_held":%d}').replace('ackcount,pads,spc)', 'ackcount,pads,spc,copied,oldframes)')
  lua=lua.replace("f:close();captured=commits;publish(pendingAck)","f:close();previousScreen=buf;captured=commits;publish(pendingAck)")
  # Every complete frame while copying must still match the previous display.
  lua=lua.replace("local st=emu.getState()\n if pendingAck", "local st=emu.getState()\n if not REFERENCE and previousScreen and packet and packetbyte(0)==3 and (rd(0x1025)==0xe2 or rd(0x1025)==0xe3) then\n local now=emu.getScreenBuffer();for i=1,#now do assert(now[i]==previousScreen[i],'mixed visible frame')end;oldframes=oldframes+1\n end\n if pendingAck")
  (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\nlocal REFERENCE='+str(reference).lower()+'\n'+lua,encoding='utf8',newline='\n')
  rom=a.out/('reference' if reference else 'client')/'sink165.sfc'
  with (d/'producer.log').open('wb') as cf,(d/'mesen.log').open('wb') as mf:
   c=subprocess.Popen([str(a.out/'producer.exe'),str(a.video/'frame12'),str(a.video/'frame15'),mode],cwd=d,env=env,stdout=cf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(rom),'--timeout=240','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=250);cr=c.wait(timeout=20)
   finally:
    for child in [m,c]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==cr==0,((d/'mesen.log').read_text(errors='replace')[-1800:],(d/'producer.log').read_text(errors='replace')[-1000:])
  q=json.loads((d/'consumer-result.json').read_bytes());q.update(mode=mode,reference=reference)
  if not reference:
   for i in range(1,4):assert (d/f'frame-{i}.rgb').read_bytes()==(a.video/f'expected-{min(i,2)}.rgb').read_bytes(),(mode,i,'baseline pixels')
   if mode!='stop':
    for i in range(1,7):assert (d/f'frame-{i}.rgb').read_bytes()==(a.out/(mode+'-reference')/f'frame-{i}.rgb').read_bytes(),(mode,i,'oracle pixels')
  results.append(q);print(json.dumps(q),flush=True)
 result=dict(passed=True,client=client,cases=results,public_sources={n:sha(ROOT/n) for n in sources},scope='Actual65816 plus actual C sink with file mailbox; E2/E3 full back-slot build, palette/OAM/HDMA flip, six pixel-exact commits and STOP. Not physical SPI/FPS.',inputs={'video':{f.relative_to(a.video).as_posix():sha(f) for f in a.video.rglob('*') if f.is_file()}})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS BANKED169')
if __name__=='__main__':main()
