# SPDX-License-Identifier: MIT
"""Check unchanged ACK acceptance, then real SNES E2/E3 rejection capture."""
from pathlib import Path
import argparse,json,subprocess,os,shutil
from nes_game147 import ROOT,sha
from nes_sink_trace168 import sink_source
from build_nes_sink165 import build
from build_nes_game164 import palette
from nes_trace166 import receiver
from test_nes_native_runtime165 import MODULES

def main():
 p=argparse.ArgumentParser()
 for n in ['out','gcc','mesen','video','trace']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 for n in vars(a):setattr(a,n,getattr(a,n).resolve())
 assert a.out.as_posix().isascii();a.out.mkdir(parents=True,exist_ok=False)
 sources=[f'src/nes/firmware/{n}.{e}' for n in MODULES+['nes_sink_trace168','nes_trace166'] for e in ['c','h']]+['tests/nes-functional/native_sink168_host.c','tests/nes-functional/native_sink165_host.c','tests/nes-functional/native_runtime165_host.c','tools/nes_sink_trace168.py','tools/test_nes_sink168.py','tools/build_nes_sink165.py','tools/nes_native_local165.py','snes/video_probe/capture_native_sink165.lua']
 for n in sources:shutil.copyfile(ROOT/n,a.out/Path(n).name)
 f=a.out/'nes_native_sink165.c';f.write_text(sink_source(f.read_text()),encoding='utf8')
 f=a.out/'nes_native165.c';f.write_text(receiver(f.read_text()),encoding='utf8')
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 def run(args,label):
  with (a.out/(label+'.log')).open('wb') as f:q=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  assert q.returncode==0,(a.out/(label+'.log')).read_text(errors='replace')[-3000:]
 common=[a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-I','.']
 run(common+['native_sink168_host.c','nes_native_sink165.c','nes_sink_trace168.c','-o','unit.exe'],'unit-build')
 run([a.out/'unit.exe'],'unit')
 run(common+['native_runtime165_host.c',*[n+'.c' for n in MODULES+['nes_trace166','nes_sink_trace168']],'-o','runtime.exe'],'runtime-build')
 shutil.copyfile(a.trace,a.out/'native-transactions.txt');(a.out/'palette.bin').write_bytes(palette())
 run([a.out/'runtime.exe','native-transactions.txt','palette.bin'],'runtime')
 s=(a.out/'native_sink165_host.c').read_text();s='#include "nes_sink_trace168.h"\n'+s
 anchor=' bool ok=nes_sink165_seal(&s,&p,5000);'
 assert s.count(anchor)==1
 s=s.replace(anchor,''' if(gen==17){
  for(unsigned i=0;i<(!strcmp(mode,"overflow")?34u:1u);i++)p.map[64*i]^=0xff;
 }
 bool ok=nes_sink165_seal(&s,&p,gen==17&&!strcmp(mode,"budget")?1:5000);
 if(gen==17){
  assert(!ok&&s.error==3&&nes_sink_trace168.valid&&nes_sink_trace168.ack_valid);
  assert(nes_sink_trace168.request[0]==3&&nes_sink_trace168.ack[0]==(!strcmp(mode,"overflow")?0xe2:0xe3)&&nes_sink_trace168.mismatch==1);
  char text[256];int n=nes_sink168_format(text,sizeof text);assert(n>0);
  FILE *f=fopen("first-failure.txt","wb");assert(f&&fwrite(text,1,(unsigned)n,f)==(unsigned)n);fclose(f);return;
 }''')
 begin=s.index('  assert(nes_sink165_begin(&s,17));');end=s.index('\n }\n FILE *f=fopen("producer-done',begin)
 s=s[:begin]+'  scene(argv[2],17); /* Real local diff failure, no host-injected ACK. */'+s[end:]
 (a.out/'producer168.c').write_text(s,encoding='utf8')
 run(common+['producer168.c','nes_native_sink165.c','nes_sink_trace168.c','-o','producer.exe'],'producer-build')
 client=build(a.out/'client');cases=[]
 for mode in ['overflow','budget']:
  d=a.out/mode;d.mkdir();lua='local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+(ROOT/'snes/video_probe/capture_native_sink165.lua').read_text()
  (d/'capture.lua').write_text(lua,encoding='utf8')
  with (d/'producer.log').open('wb') as cf,(d/'mesen.log').open('wb') as mf:
   c=subprocess.Popen([str(a.out/'producer.exe'),str(a.video/'frame12'),str(a.video/'frame15'),mode],cwd=d,env=env,stdout=cf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/sink165.sfc'),'--timeout=180','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=190);cr=c.wait(timeout=15)
   finally:
    for child in [m,c]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==cr==0,((d/'mesen.log').read_text(errors='replace')[-3000:],(d/'producer.log').read_text(errors='replace')[-2000:])
  q=json.loads((d/'consumer-result.json').read_bytes());assert q['commits']==3
  for i in range(1,4):assert (d/f'frame-{i}.rgb').read_bytes()==(a.video/f'expected-{min(i,2)}.rgb').read_bytes()
  trace=dict(line.split('=',1) for line in (d/'first-failure.txt').read_text().splitlines());assert trace['sink_trace_mismatch_hex']=='01'
  q.update(mode=mode,first_failure=trace,pixels=3*256*239);cases.append(q)
 result=dict(passed=True,unit=(a.out/'unit.log').read_text(),runtime=(a.out/'runtime.log').read_text(),cases=cases,client=client,public_sources={n:sha(ROOT/n) for n in sources},generated_sources={f.name:sha(f) for f in a.out.glob('*.c')},inputs={'trace':sha(a.trace),'mesen':sha(a.mesen),'video':{f.relative_to(a.video).as_posix():sha(f) for f in a.video.rglob('*') if f.is_file()}},scope='Real SNES E2/E3 from deliberate map changes/budget1. Actual C sink records rejection,3 previous display ACKs/pixels preserved. File mailbox, NOT physical SPI or proof that167 saw E2/E3. Existing FPGA unchanged.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['passed','unit','cases']}))
if __name__=='__main__':main()
