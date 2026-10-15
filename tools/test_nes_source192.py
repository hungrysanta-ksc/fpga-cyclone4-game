# SPDX-License-Identifier: MIT
"""Actual191 plans/C outputs -> candidate192 -> deployed arbiter/READ16 pins.
Pin data is a70ns fixture; qualified schedule is optimistic NTSC, not live CPU.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=ROOT.parent/'probes/nes-window184-coupled/evidence/route02'
 ref=ROOT.parent/'probes/nes-plan191/test03';pins={};names=[]
 for source in [board/'nes_native_arbiter165.sv',board/'nes_rom_physical.sv',
                ROOT/'src/nes/rtl/nes_tile191.sv',ROOT/'src/nes/rtl/nes_source_tile192.sv',ROOT/'src/nes/rtl/nes_chr_cache192.sv',
                ROOT/'tests/nes-functional/source_tile192_tb.sv']:
  shutil.copyfile(source,a.out/source.name);names.append(source.name)
  pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
 for scene in range(8):
  for ext in ('mem','rtl','expected'):
   source=ref/f'scene{scene}.{ext}';shutil.copyfile(source,a.out/source.name)
   pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
 def run(tool,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-6000:]
  return s
 run('vlib',['work'],'vlib');run('vlog',['-sv',*names],'vlog')
 results=[]
 for scene,mode,phase in [(i,0,0 if i%2==0 else 3.5) for i in range(8)]+[(0,1,3.5),(0,2,3.5)]:
  label=f'scene{scene}-mode{mode}'
  s=run('vsim',['-c','work.source_tile192_tb',f'-gSCENE={scene}',f'-gMODE={mode}',f'-gPHASE={phase}',
                '-do','onerror {quit -code 1}; run -all; quit -f'],label)
  if mode==2:
   assert 'PASS SOURCE192FAULT cases=9' in s;continue
  m=re.search(r'PASS SOURCE192 scene=(\d+) mode=(\d+) tiles=(\d+) bytes=(\d+) reads=(\d+) core=(\d+) windows=(\d+) first=(\d+) last=(\d+) cycles=(\d+)',s);assert m
  r=dict(zip(('scene','mode','tiles','bytes','reads','core_reads','read_windows','first_read_cycle','last_read_cycle','cycles'),map(int,m.groups())))
  r['phase_ns']=phase;r['synthetic_elapsed_ms']=r['cycles']*46.560846/1e6
  results.append(r)
 baseline=json.loads((ref/'result.json').read_bytes())['cases']
 for case,old in zip(results[:8],baseline):
  assert case['tiles']==old['plans'] and case['bytes']==old['output_bytes'] and case['reads']<=old['reads']
 assert results[8]['tiles']==512 and results[8]['bytes']==8192 and results[8]['reads']==16
 result=dict(passed=True,cases=results,negative_cases=9,source_pins=pins,scope=__doc__,
             wire_or_aperture_connected=False,production_epoch_source=False,actual_game=False,new_fit=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,cases=results,negative_cases=9),indent=2))
if __name__=='__main__':main()
