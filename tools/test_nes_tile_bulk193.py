# SPDX-License-Identifier: MIT
"""Actual192 READ16 -> tile CDC ->188 raw bus, same actual186 C reference.
Synthetic correctness/backpressure only; NOT the required first-level scroll measurement.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=ROOT.parent/'probes/nes-window184-coupled/evidence/route02'
 ref=ROOT.parent/'probes/nes-plan191/test03';pins={};names=[]
 for n in ('nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv'):
  source=board/n;shutil.copyfile(source,a.out/n);names.append(n);pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
 for n in ('nes_tile191.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_bulk_aperture188.sv','nes_tile_bulk193.sv'):
  source=ROOT/'src/nes/rtl'/n;shutil.copyfile(source,a.out/n);names.append(n);pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
 for n in ('source_tile192_tb.sv','tile_bulk193_consumer.svh'):
  source=ROOT/'tests/nes-functional'/n;shutil.copyfile(source,a.out/n);pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
 s=(a.out/'source_tile192_tb.sv').read_text()
 def replace(before,after):
  nonlocal s
  assert s.count(before)==1,before;s=s.replace(before,after)
 replace('module source_tile192_tb;','module tile_bulk193_tb;')
 replace('wire out_ready=cycle%5!=0;', 'wire out_ready;')
 replace('reg [7:0] memory[0:159],expected[0:32767];','reg [7:0] memory[0:159],expected[0:32767];\n `include "tile_bulk193_consumer.svh"')
 replace('for(j=0;j<512;j=j+1)begin submit();complete();end','for(j=0;j<512;j=j+1)begin slot=j+1;submit();complete();end')
 replace('$fclose(f);', '$fclose(f);finish_bulk();')
 replace('if(!checked||!core_reads||!stall)', 'if(!checked||!core_reads)')
 # Only normal scenarios and pressure are used;192 lifetime tests stay frozen.
 (a.out/'tile_bulk193_tb.sv').write_text(s,encoding='utf8',newline='\n');names.append('tile_bulk193_tb.sv')
 for scene in range(8):
  for ext in ('mem','rtl','expected'):
   source=ref/f'scene{scene}.{ext}';shutil.copyfile(source,a.out/source.name);pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
 def run(tool,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-6000:]
  return s
 run('vlib',['work'],'vlib');run('vlog',['-sv',*names],'vlog')
 cases=[]
 for scene,mode in [(i,0) for i in range(8)]+[(0,1)]:
  s=run('vsim',['-c','work.tile_bulk193_tb',f'-gSCENE={scene}',f'-gMODE={mode}','-gPHASE=3.5',
    '-do','onerror {quit -code 1}; run -all; quit -f'],f'scene{scene}-mode{mode}')
  m=re.search(r'PASS BULK193 scene=(\d+) mode=(\d+) bytes=(\d+) chunks=(\d+) fullwait=(\d+) sourcewait=(\d+) wrong=(\d+)',s);assert m
  c=dict(zip(('scene','mode','bytes','chunks','full_wait_host_cycles','source_wait_nes_cycles','wrong_token_checks'),map(int,m.groups())));cases.append(c)
 assert sum(c['bytes'] for c in cases[:8])==1840 and cases[-1]['bytes']==8192 and cases[-1]['chunks']==4
 result=dict(passed=True,cases=cases,source_pins=pins,generated_tb_sha256=sha(a.out/'tile_bulk193_tb.sv'),
  scope=__doc__,actual_scroll_measured=False,actual_snes_cpu=False,production_control_decoder=False,new_fit=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(passed=True,cases=cases)))
if __name__=='__main__':main()
