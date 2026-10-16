# SPDX-License-Identifier: MIT
"""Actual186 C planning -> bounded tile191 RTL -> actual186 BG/OBJ bytes.
Synthetic committed scenes/sealed memory, not live game, PSRAM/CPU/DMA or FIT.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_plan191 import ROOT,sha,prepare
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 pins=prepare(a.out/'candidate')
 for f in (a.out/'candidate').iterdir():shutil.copyfile(f,a.out/f.name)
 arm=ROOT.parent/'probes/nes-paired186/arm01/src'
 for n in ('nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h','nes_native_video165.c','nes_native_video165.h'):
  shutil.copyfile(arm/n,a.out/n);pins['production/'+n]=sha(arm/n)
 for n in ('tests/nes-functional/plan191_host.c','tests/nes-functional/tile191_tb.sv','src/nes/rtl/nes_tile191.sv'):
  shutil.copyfile(ROOT/n,a.out/Path(n).name);pins[n]=sha(ROOT/n)
 def run(exe,args,label):
  env=os.environ.copy();env['PATH']=str(exe.parent)+os.pathsep+env.get('PATH','')
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:]
  return s
 gcc=a.questa_bin.parent/'gcc-7.4.0-mingw64vc16/bin/gcc.exe'
 run(gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','plan191_host.c','nes_plan191.c','nes_native_video165.c','nes_native165.c','nes_trace166.c','-o','host.exe'],'gcc')
 host=run(a.out/'host.exe',[],'host');assert 'PASS PLAN191 scenes=8' in host
 sizes=[]
 for scene in range(8):
  lines=[];plan_bytes=0;expected_size=0;cross=0
  for line in (a.out/f'scene{scene}.plans').read_text().splitlines():
   v=list(map(int,line.split()));assert len(v)==29
   k,g,slot,tag,mask=v[:5];rows=v[5:21];alt=v[21:]
   assert all(x<8 for x in rows)
   rm=sum(x<<(i*3) for i,x in enumerate(rows));am=sum((x!=65535)<<i for i,x in enumerate(alt))
   at=sum((0 if x==65535 else x)<<(i*13) for i,x in enumerate(alt));cross+=bool(am)
   lines.append(f'{k:x} {g:x} {slot:x} {tag:x} {mask:x} {rm:012x} {am:02x} {at:026x}\n')
   plan_bytes+=16+2*am.bit_count();expected_size+=32 if k==1 else 16
  (a.out/f'scene{scene}.rtl').write_text(''.join(lines),encoding='ascii')
  assert len((a.out/f'scene{scene}.expected').read_text().split())==expected_size
  sizes.append(dict(scene=scene,plans=len(lines),plan_bytes=plan_bytes,output_bytes=expected_size,cross_tile_plans=cross))
 run(a.questa_bin/'vlib.exe',['work'],'vlib')
 run(a.questa_bin/'vlog.exe',['-sv','nes_tile191.sv','tile191_tb.sv'],'vlog')
 for s in sizes:
  t=run(a.questa_bin/'vsim.exe',['-c','work.tile191_tb',f'-gSCENE={s["scene"]}','-do','onerror {quit -code 1}; run -all; quit -f'],f'rtl{s["scene"]}')
  m=re.search(r'PASS TILE191 scene=(\d+) tiles=(\d+) bytes=(\d+) reads=(\d+) stalls=(\d+) cycles=(\d+)',t);assert m
  assert int(m[2])==s['plans'] and int(m[3])==s['output_bytes']
  s.update(reads=int(m[4]),output_stalls=int(m[5]),cycles=int(m[6]))
 pins['generator']=sha(ROOT/'tools/nes_plan191.py');pins['runner']=sha(Path(__file__))
 result=dict(passed=True,cases=sizes,pins=pins,host_summary=host.strip(),scope=__doc__,new_fit=False,new_firmware=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,cases=sizes),indent=2))
if __name__=='__main__':main()
