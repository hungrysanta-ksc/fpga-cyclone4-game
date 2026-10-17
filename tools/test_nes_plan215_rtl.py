# SPDX-License-Identifier: MIT
"""C service + selected207 SPI/lease/READ16/bulk; modeled SNES ACK, not FPS."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,time
from test_nes_join208 import prepare,ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--service',type=Path);a=p.parse_args();a.out=a.out.resolve()
 assert str(a.out).isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 pins,rtl=prepare(a.out);src=BASE/'probes/nes-startup214/arm02/src'
 for f in src.glob('nes_*.h'):shutil.copyfile(f,a.out/f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 service=a.service or src/'nes_plan_service200.c';shutil.copyfile(service,a.out/'nes_plan_service200.c');pins[str(service)]=sha(service)
 if a.service:
  header=service.parent/'nes_plan215.h';shutil.copyfile(header,a.out/header.name);pins[str(header)]=sha(header)
 f=ROOT/'tests/nes-functional/plan215_host.c';shutil.copyfile(f,a.out/'host.c');pins[f.relative_to(BASE).as_posix()]=sha(f)
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');qb=Path('C:/altera_standard/25.1std/questa_fse/win64')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-O2','host.c','nes_plan_service200.c','-o','host.exe'],'gcc-host')
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-shared','join208_rpc.c','-o','join208_rpc.dll'],'gcc-rpc')
 run([qb/'vlib.exe','work'],'vlib');run([qb/'vlog.exe','-sv',*rtl,'join208_tb.sv'],'vlog')
 children=[];logs=[]
 try:
  for n,cmd in [('rtl',[qb/'vsim.exe','-c','-sv_lib','join208_rpc','work.join208_tb','-do','onerror {quit -code 1}; run -all; quit -f']),('host',[a.out/'host.exe'])]:
   f=(a.out/(n+'.log')).open('wb');logs.append(f);children.append(subprocess.Popen(list(map(str,cmd)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
  start=time.monotonic()
  while any(c.poll() is None for c in children):
   if any(c.poll() not in (None,0) for c in children) or time.monotonic()-start>600:break
   if '** Fatal:' in (a.out/'rtl.log').read_text(errors='replace'):break
   time.sleep(.1)
  codes=[c.poll() for c in children]
 finally:
  for c in children:
   if c.poll() is None:c.kill();c.wait()
  for f in logs:f.close()
 texts={n:(a.out/(n+'.log')).read_text(errors='replace') for n in ['rtl','host']}
 passed=codes==[0,0] and 'PASS PLAN215 frames=20' in texts['host'] and 'PASS JOIN208 RTL' in texts['rtl']
 result=dict(passed=passed,codes=codes,source_pins=pins,public_sha=sha(Path(__file__)),scope=__doc__,physical=False,full_game=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result|{'source_pins':None}),flush=True)
 assert passed,{n:t[-4000:] for n,t in texts.items()}
if __name__=='__main__':main()
