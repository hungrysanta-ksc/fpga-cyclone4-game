# SPDX-License-Identifier: MIT
"""Production C+window/actual65816; save exact SPI and consumer events for RTL replay."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys
from nes_game147 import ROOT,sha
from nes_clip178 import replace
from test_nes_client181 import expected

def main():
 p=argparse.ArgumentParser()
 for n in ['out','arm','fixtures','prior','gcc','mesen']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--client',type=Path,help='Explicit candidate SNES client; defaults to the archived prior client')
 a=p.parse_args()
 for n in vars(a):
  if getattr(a,n) is not None:setattr(a,n,getattr(a,n).resolve())
 a.out.mkdir(parents=True,exist_ok=False);pins={}
 for n in ['nes_native_sink165.c','nes_native_sink165.h','nes_native_video165.h','nes_native165.h','nes_sink_trace168.c','nes_sink_trace168.h','nes_sink_window184.c','nes_sink_window184.h']:
  shutil.copyfile(a.arm/n,a.out/n);pins[n]=sha(a.arm/n)
 host=(a.prior/'host.c').read_text();start=host.index('static bool exchange(');end=host.index('static unsigned read_file(',start)
 host=host[:start]+(ROOT/'tests/nes-functional/window184_filebus.inc').read_text()+'\n'+host[end:]
 host=replace(host,'mode=argv[2];nes_sink165_reset(&sink,exchange,NULL);','''mode=argv[2];events=fopen("events.txt","w");assert(events);
 assert(nes_window184_init(&window,queued_transfer,queued_guard,NULL,65536));
 nes_sink165_reset(&sink,nes_window184_barrier,&window);sink.enqueue=nes_window184_enqueue;''')
 host=replace(host,'assert(nes_sink_trace168.ack[0]==(!strncmp(mode,"stop",4)?0xe4:0xe0));','assert(queue_fault&&window.error==4&&last_ack[0]==0xe4);')
 # STOP in the middle of DATA5 can be noticed while later DATA is being queued.
 host=replace(host,'assert(nes_sink165_pattern(&sink,0,i,pattern+i*16,n*16));','if(!nes_sink165_pattern(&sink,0,i,pattern+i*16,n*16))return false;')
 host=replace(host,'assert(nes_sink165_pattern(&sink,1,i,pattern+i*32,n*32));','if(!nes_sink165_pattern(&sink,1,i,pattern+i*32,n*32))return false;')
 host=replace(host,' done:;',''' done:;
 assert(max_used==4 && calls==guards);
 if(!strcmp(mode,"normal"))assert(!queue_fault&&accepted==retired&&window.sent==window.retired);
 fprintf(events,"E 0 0 0\\n");fclose(events);
 FILE *result=fopen("window-result.json","w");assert(result);
 fprintf(result,"{\\"accepted\\":%u,\\"retired\\":%u,\\"max_used\\":%u,\\"calls\\":%u,\\"guards\\":%u,\\"error\\":%u}\\n",accepted,retired,max_used,calls,guards,window.error);fclose(result);''')
 (a.out/'host.c').write_text(host,encoding='utf8',newline='\n')
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'gcc.log').open('wb') as f:
  q=subprocess.run([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2','host.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','-o','host.exe'],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(a.out/'gcc.log').read_text(errors='replace')
 shutil.copytree(a.client or a.prior/'client',a.out/'client');cases=[]
 lua=(a.prior/'normal/capture.lua').read_text().split('\n',2)[2]
 for mode in ['normal','stop_copy','stop_long']:
  d=a.out/mode;d.mkdir();script=lua
  # STOP producer may already have queued later packets. They stay owned by
  # the faulted queue and are not made visible to the SNES after the error ACK.
  script=replace(script,'if not packet then local f=', 'if not packet and not rejected then local f=')
  (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+script,encoding='utf8')
  with (d/'host.log').open('wb') as hf,(d/'mesen.log').open('wb') as mf:
   h=subprocess.Popen([str(a.out/'host.exe'),str(a.fixtures),mode],cwd=d,env=env,stdout=hf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/sink165.sfc'),'--timeout=70','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=80);hr=h.wait(timeout=5)
   finally:
    for child in [h,m]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==hr==0,((d/'mesen.log').read_text(errors='replace')[-2000:],(d/'host.log').read_text(errors='replace')[-1000:])
  frames=[(0,0),(7,0),(7,1),(0,0),(0,0),(1,0),(7,2)] if mode=='normal' else [(0,0)]
  for i,(count,phase) in enumerate(frames,1):
   actual=(d/f'frame-{i}.rgb').read_bytes();gold=expected(count,phase)
   assert actual==gold,(mode,i,sum(x!=y for x,y in zip(actual,gold)))
  result=json.loads((d/'consumer-result.json').read_bytes());result.update(mode=mode,window=json.loads((d/'window-result.json').read_bytes()),events_sha256=sha(d/'events.txt'),pixels=len(frames)*256*239)
  cases.append(result);print(json.dumps(result),flush=True)
 result=dict(passed=True,cases=cases,arm_sources=pins,prior_host=sha(a.prior/'host.c'),prior_lua=sha(a.prior/'normal/capture.lua'),snes_rom=sha(a.out/'client/sink165.sfc'),
  public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_window184_coupled.py','tests/nes-functional/window184_filebus.inc']},scope=__doc__,rtl_replay_pending=True,physical=False,fps60=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
