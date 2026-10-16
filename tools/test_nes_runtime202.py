# SPDX-License-Identifier: MIT
"""Actual production C RUN/receiver/planner/window/sink; modeled hardware SPI.
Nine sequential geometry scenes, real packet CRC/count/COMMIT, source-derived
BG/OBJ pixels against186 converter. Not RTL/65816/physical timing evidence.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_runtime202 import ROOT,BASE,prepare,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve()
 prep=prepare(a.out);pins=prep['source_pins']
 for n in ('runtime202_host.c','plan191_host.c'):
  f=ROOT/'tests/nes-functional'/n;shutil.copyfile(f,a.out/n);pins[f.relative_to(BASE).as_posix()]=sha(f)
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as log:
   r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,s[-6000:];return s
 sources=['runtime202_host.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_plan191.c','nes_plan_service200.c','nes_native_video165.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c']
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fstack-usage',*sources,'-o','host.exe'],'gcc')
 s=run([a.out/'host.exe'],'host');assert 'PASS RUNTIME202 frames=9 ' in s and s.count('PASS RUNTIME202 fault=')==6
 result=dict(passed=True,frames=9,fault_cases=6,source_pins=pins,script_sha256=sha(Path(__file__)),compiler_sha256=sha(gcc),
  scope=__doc__,summary=s.strip(),real_receiver=True,real_planner=True,real_run_loop=True,real_window_sink=True,
  hardware_modeled=True,rtl_cosimulation=False,actual_snes_cpu=False,full_arm=False,new_fit=False,new_package=False,actual_scroll_measured=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(s)
if __name__=='__main__':main()
