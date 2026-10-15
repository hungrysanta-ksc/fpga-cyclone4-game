# SPDX-License-Identifier: MIT
"""C encoded plans -> dual-clock RAM decoder ->192 READ16 ->193 aperture.
Same archived actual186 C pixels; synthetic source, not a scrolling workload.
No SPI/production epoch/controller or actual SNES CPU connected in this test.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from nes_clip178 import replace
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=ROOT.parent/'probes/nes-window184-coupled/evidence/route02';ref=ROOT.parent/'probes/nes-plan191/test03';pins={};names=[]
 def copy(f):
  shutil.copyfile(f,a.out/f.name);pins[f.relative_to(ROOT.parent).as_posix()]=sha(f)
 for n in ('nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv'):
  copy(board/n);names.append(n)
 for n in ('nes_tile191.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_bulk_aperture188.sv','nes_tile_bulk193.sv','nes_plan_stream196.sv'):
  copy(ROOT/'src/nes/rtl'/n);names.append(n)
 for n in ('source_tile192_tb.sv','tile_bulk193_consumer.svh','plan196_host.c','plan196_driver.svh','plan196_boundary_tb.sv'):
  copy(ROOT/'tests/nes-functional'/n)
 for n in ('nes_plan191.h','nes_plan_wire196.h'):copy(ROOT/'src/nes/firmware'/n)
 for n in ('nes_native_video165.h','nes_native165.h','nes_trace166.h'):
  copy(ROOT.parent/'probes/nes-paired186/arm01/src'/n)
 for scene in range(8):
  for ext in ('mem','rtl','expected','plans'):copy(ref/f'scene{scene}.{ext}')
 s=(a.out/'source_tile192_tb.sv').read_text()
 s=replace(s,'module source_tile192_tb;','module plan_stream196_tb;\n parameter integer EXTERNAL=1;')
 s=replace(s,'wire out_ready=cycle%5!=0;', 'wire out_ready;\n `include "plan196_driver.svh"')
 s=replace(s,'#(.USE_CACHE(USE_CACHE))','#(.USE_CACHE(USE_CACHE),.EXTERNAL_PLAN(EXTERNAL))')
 for n,v in [('valid','pv'),('ready','pr'),('kind','kind'),('generation','gen'),('slot','slot'),('tag','tag'),('rows','rows'),('mask','mask'),('alt_mask','am'),('alt_tags','ats')]:
  s=replace(s,f'.plan_{n}({v})',f'.plan_{n}({v}196)')
 s=replace(s,'reg [7:0] memory[0:159],expected[0:32767];','reg [7:0] memory[0:159],expected[0:32767];\n `include "tile_bulk193_consumer.svh"')
 s=replace(s,'begin while(!pr&&!fault)tick();if(fault)$fatal(1,"not ready");@(negedge clk);pv=1;tick();@(negedge clk);pv=0;end','begin submit_wire();end')
 s=replace(s,'$fclose(f);','$fclose(f);finish_bulk();')
 s=replace(s,'if(!checked||!core_reads||!stall)','if(!checked||!core_reads)')
 (a.out/'plan_stream196_tb.sv').write_text(s,encoding='utf8',newline='\n')
 s=(a.out/'tile_bulk193_consumer.svh').read_text()
 s=replace(s,'reg ev=0,consume=0;wire er,','reg consume=0;wire ev=ev196;wire er;assign er196=er;wire ')
 s=replace(s,'while(!er)tick();@(negedge clk);ev=1;tick();@(negedge clk);ev=0;','submit_wire();')
 (a.out/'tile_bulk193_consumer.svh').write_text(s,encoding='utf8',newline='\n')
 env=os.environ.copy()
 def run(exe,args,label):
  env['PATH']=str(exe.parent)+os.pathsep+os.environ.get('PATH','')
  with (a.out/(label+'.log')).open('wb') as log:
   r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-5000:]
  return text
 gcc=a.questa_bin.parent/'gcc-7.4.0-mingw64vc16/bin/gcc.exe'
 run(gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','plan196_host.c','-o','host.exe'],'gcc')
 host=run(a.out/'host.exe',[ref],'host');assert 'plans=97 bytes=1580 boundaries=268' in host
 run(a.questa_bin/'vlib.exe',['work'],'vlib')
 run(a.questa_bin/'vlog.exe',['-sv',*names,'plan_stream196_tb.sv','plan196_boundary_tb.sv'],'vlog')
 boundary=run(a.questa_bin/'vsim.exe',['-c','work.plan196_boundary_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'boundary')
 assert 'PASS PLAN196BOUNDARY checks=273' in boundary,boundary[-2000:]
 cases=[]
 for scene,external in [(i,1) for i in range(8)]+[(7,0)]:
  label=f'scene{scene}-external{external}'
  t=run(a.questa_bin/'vsim.exe',['-c','work.plan_stream196_tb',f'-gSCENE={scene}',f'-gEXTERNAL={external}','-gPHASE=3.5','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  m=re.search(r'PASS BULK193 scene=(\d+) mode=(\d+) bytes=(\d+) chunks=(\d+) fullwait=(\d+) sourcewait=(\d+) wrong=(\d+)',t);assert m
  cases.append(dict(scene=scene,external_plan=external,bytes=int(m[3]),chunks=int(m[4]),source_wait=int(m[6])))
 assert sum(c['bytes'] for c in cases[:8])==1840
 result=dict(passed=True,scope=__doc__,cases=cases,host=host.strip(),boundary_checks=273,source_pins=pins,
  script_sha256=sha(Path(__file__)),generated_tb_sha256=sha(a.out/'plan_stream196_tb.sv'),
  generated_consumer_sha256=sha(a.out/'tile_bulk193_consumer.svh'),compiler_sha256=sha(gcc),
  actual_scroll_measured=False,new_fit=False,new_firmware=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(passed=True,cases=cases,checks=273)))
if __name__=='__main__':main()
