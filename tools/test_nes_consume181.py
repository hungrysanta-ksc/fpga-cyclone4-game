# SPDX-License-Identifier: MIT
"""Actual181 receiver/converter/sink; emitted bytes to a direct SNES test ROM.

Mailbox callback captures and validates real C packets but synthesizes ACKs.
The actual production SNES packet decoder/banked upload is NOT integrated here.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,os,re,shutil,struct,subprocess
from build_nes_game164 import palette
import test_nes_patch181_snes as prototype
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('baseline','out','gcc','arm-bin','mesen'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True);sources={}
 prep=json.loads((a.baseline.parent/'preparation-minreject180.json').read_bytes());pins={**prep['copied'],**prep['changed'],**prep['added']}
 old=['nes_native_sink165.h','nes_trace166.h','nes_trace166.c','nes_sink_trace168.h','nes_sink_trace168.c']
 for n in old:
  assert sha(a.baseline/n)==pins['src/'+n];shutil.copy2(a.baseline/n,a.out/n);sources['baseline/'+n]=sha(a.baseline/n)
 new=['src/nes/firmware/'+n for n in ['nes_native181.h','nes_native181.c','nes_native_video181.h','nes_native_video181.c','nes_native_sink181.c']]+['tests/nes-functional/consume181_host.c']
 for n in new:
  shutil.copy2(ROOT/n,a.out/Path(n).name.replace('181.','165.') if Path(n).name.startswith('nes_') else a.out/Path(n).name);sources[n]=sha(ROOT/n)
 def run(exe,args,name,cwd=None,env=None):
  cwd=cwd or a.out
  with (cwd/(name+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(cwd/(name+'.log')).read_text(errors='replace');assert r.returncode==0,s[-5000:];return s
 d=a.out/'old';d.mkdir()
 for n in ['nes_native165.h','nes_native_video165.h','nes_native_video165.c']:
  assert sha(a.baseline/n)==pins['src/'+n];shutil.copy2(a.baseline/n,d/n);sources['baseline/'+n]=sha(a.baseline/n)
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-Dnes_native_video165_build=legacy_build','-c','nes_native_video165.c','-o','legacy.o'],'gcc',d)
 files=['nes_native165.c','nes_native_video165.c','nes_native_sink165.c','nes_trace166.c','nes_sink_trace168.c']
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'consume181_host.c',d/'legacy.o','-o','host.exe'],'gcc')
 sizes=[]
 for variant,path in [('old',d),('new',a.out)]:
  (path/'layout.c').write_text('#include "nes_native_video165.h"\nchar video_size[sizeof(struct nes_native_video165)];\nchar receiver_size[sizeof(struct nes_native165)];\n',encoding='utf8')
  run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-c','nes_native_video165.c','layout.c'],'arm',path)
  nm=run(a.arm_bin/'arm-none-eabi-nm.exe',['-S','layout.o'],'nm',path)
  sizes.append({n:int(re.search(r'\w+\s+([\da-f]+)\s+\w\s+'+n,nm)[1],16) for n in ('video_size','receiver_size')})
 assert sizes[0]==sizes[1],sizes
 run(a.arm_bin/'arm-none-eabi-gcc.exe',['-std=c11','-Wall','-Wextra','-Werror','-mcpu=cortex-m4','-mthumb','-Os','-fstack-usage','-c','nes_native_sink165.c'],'sink-arm')
 results=[];cases={}
 for count,phase in [(0,0),(1,0),(7,0),(7,1),(7,2)]:
  d=a.out/f'rows{count}-phase{phase}';d.mkdir();(d/'palette.bin').write_bytes(palette());cases[count,phase]=d
  text=run(a.out/'host.exe',[count,phase,d/'palette.bin'],'host',d);print(text.strip(),flush=True)
  assert 'PASS CONSUME181' in text;checks=int(re.search(r'checks=(\d+)',text)[1]);results.append(dict(patches=count,phase=phase,checks=checks))
  if count:
   rows=prototype.ROWS[:count] if phase<2 else [128+s*8 for s in range(7)]
   ref=prototype.encode([(y,bytes(prototype.raw(y,x,phase) for x in range(256))) for y in rows],0)
   assert (d/'raw.bin').read_bytes()==ref['chr']
   assert (d/'mode-a.bin').read_bytes()==ref['hdma'][0]
   assert (d/'mode-b.bin').read_bytes()==prototype.encode([(y,bytes(prototype.raw(y,x,phase) for x in range(256))) for y in rows],1)['hdma'][0]
   # Enable table additionally switches the clip window in181 (old prototype
   # did not model clipping). Independently expand all224 row descriptors.
   table=(d/'enable.bin').read_bytes();decoded=[];at=0
   while table[at]:
    n=table[at];decoded.extend([tuple(table[at+1:at+5])]*n);at+=5
   assert at+1==len(table) and len(decoded)==224
   assert decoded==[(1,0,0,0) if y in rows else (17,0,17 if phase else 0,0) for y in range(224)]
   bundle=(d/'bundle.bin').read_bytes();assert len(bundle)==3418
   assert bundle[:len((d/'hdma.bin').read_bytes())]==(d/'hdma.bin').read_bytes()
   assert bundle[1121:3169]==ref['chr']
   for start,name in [(3169,'mode-a.bin'),(3250,'mode-b.bin'),(3331,'enable.bin')]:
    b=(d/name).read_bytes();assert bundle[start:start+len(b)]==b and not any(bundle[start+len(b):start+81])
   assert struct.unpack('<3H',bundle[3412:])==tuple(len((d/n).read_bytes()) for n in ('mode-a.bin','mode-b.bin','enable.bin'))
 # Execute actual65816/DMA/PPU using the bytes produced by actual C. The
 # uploader is a bounded test ROM, NOT a substitute for production ACK/STOP.
 out=a.out/'snes';out.mkdir();paths=[cases[7,0],cases[7,1]]
 plans=[dict(layout=prototype.LAYOUTS[i],chr=(paths[i]/'raw.bin').read_bytes(),map=prototype.encode(prototype.fixture(i),i)['map'],
  hdma=[(paths[i]/('mode-b.bin' if i else 'mode-a.bin')).read_bytes(),(paths[i]/'enable.bin').read_bytes(),(paths[i]/'hdma.bin').read_bytes()]) for i in range(2)]
 source=inspect.getsource(prototype.build)
 def edit(old,new):
  nonlocal source
  assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
 edit('plans=[encode(fixture(i),i) for i in range(2)]','plans=PLANS')
 edit('payload=bytearray()','payload=bytearray();cache={}')
 edit('source=0xc000+len(payload);payload.extend(data)','''data=bytes(data)
        if data not in cache:cache[data]=0xc000+len(payload);payload.extend(data)
        source=cache[data]''')
 edit('for a in range(0x2123,0x212c):c.store(a,0)','''for a in range(0x2123,0x212c):c.store(a,0)
    for a,v in [(0x2123,2),(0x2125,2),(0x2126,0),(0x2127,7)]:c.store(a,v)''')
 begin=source.index('    lut=palette();');end=source.index('    table_addresses=[]',begin)
 source=source[:begin]+'''    upload('cgram',0,(PATHS[0]/'cgram.bin').read_bytes())
    upload('oam',0,(PATHS[0]/'oam.bin').read_bytes())
    pattern=(PATHS[0]/'bg.bin').read_bytes();obj=(PATHS[0]/'obj.bin').read_bytes()
'''+source[end:]
 edit("upload('vram',l['map'],bytes(2048))","upload('vram',l['map'],(PATHS[i]/'map.bin').read_bytes())")
 namespace=dict(prototype.__dict__);namespace.update(PLANS=plans,PATHS=paths);exec(compile(source,'consume181-snes','exec'),namespace)
 (out/'generated-build.py').write_text(source,encoding='utf8');rom=namespace['build'](out)
 capture=ROOT/'snes/video_probe/capture_native_commands165.lua'
 (out/'capture.lua').write_text('local OUT_DIR='+json.dumps(out.as_posix())+'\n'+capture.read_text(),encoding='utf8')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 run(a.mesen,['--testRunner',out/'capture.lua',out/'native.sfc','--timeout=40','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],'mesen',out,env)
 for phase in range(2):
  gold=bytearray(prototype.expected(phase))
  if phase:
   value=struct.unpack('<64H',palette())[15];rgb=bytes((((value>>s)&31)<<3)|(((value>>s)&31)>>2) for s in (0,5,10))
   for y in range(224):
    if y not in prototype.ROWS:
     for x in range(8):gold[((y+7)*256+x)*3:((y+7)*256+x)*3+3]=rgb
  actual=(out/f'frame-{phase+1}.rgb').read_bytes();(out/f'expected-{phase+1}.rgb').write_bytes(gold)
  assert actual==gold,(phase,len(actual),len(gold),sum(x!=y for x,y in zip(actual,gold)))
 for n in ('tools/nes_patch181.py','tools/test_nes_patch181_snes.py','tools/build_nes_game164.py','tools/build_nes_trace_replay.py','snes/video_probe/capture_native_commands165.lua'):sources[n]=sha(ROOT/n)
 result=dict(passed=True,cases=results,arm_sizes=sizes,full_images=2,visible_pixels=114688,rom=rom,sources=sources,runner_sha256=sha(Path(__file__)),mesen_sha256=sha(a.mesen),production_snes_client=False,full_arm_link=False,new_fit=False,hardware=False,
 scope='Actual181 receiver->converter->sink packets; mock ACKs. Actual65816/DMA/PPU direct test upload of C-produced bytes, both banks, raw/object crossing and normal clipping. No production SNES mailbox/ACK/STOP integration or actual game.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print('PASS CONSUME181 SNES pixels=114688')
if __name__=='__main__':main()
