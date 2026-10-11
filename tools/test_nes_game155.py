# SPDX-License-Identifier: MIT
"""Short synthetic BG/CPU collision sweep through actual154/155 hardware RTL."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,ROM_SHA,VHDL,SV,EXTRA,sha
from nes_game155 import patch_ppu

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 assert sha(a.rom)==ROM_SHA;a.out.mkdir(parents=True)
 e=a.baseline/'nes-game154/evidence';pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game154-verification.json').read_bytes())['manifest_sha256']
 for n in VHDL+SV+EXTRA:
  assert sha(e/'asm'/n)==pins['asm/'+n]
  dst=a.out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.prepared/n,dst)
  if n!='rtl/ppu.sv':assert sha(dst)==pins['asm/'+n],n
 assert (a.out/'rtl/ppu.sv').read_text()==patch_ppu((e/'asm/rtl/ppu.sv').read_text())
 shutil.copy2(ROOT/'tests/nes-functional/game155_collision_tb.sv',a.out/'game155_collision_tb.sv')
 image=a.rom.read_bytes()
 for n,data in [('prg',image[16:0x40010]),('chr',image[0x40010:])]:
  (a.out/(n+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data))
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:]
  return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'game155_collision_tb.sv'],'vlog')
 results=[]
 for phase in [0,3.5,5.5]:
  for control in [0,1]:
   label=f'phase-{phase}-control-{control}'
   s=run('vsim',['-c','work.focused155_tb',f'+PHASE={phase}',f'+CONTROL={control}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
   rows=[tuple(map(int,m)) for m in re.findall(r'CASE155 offset=(\d+) failed=(\d+) error=(\d+)',s)]
   assert len(rows)==12 and 'DONE155' in s
   faults=sum(row[1] for row in rows)
   assert (faults>0 if control else faults==0),(label,rows)
   if not control:assert 'PASS155 hint gates' in s
   results.append(dict(phase_ns=phase,control=control,cases=12,faults=faults,rows=rows,log_sha256=sha(a.out/(label+'.log'))))
 result=dict(passed=True,rom_sha256=ROM_SHA,sources={n:sha(a.out/n) for n in VHDL+SV+EXTRA+['game155_collision_tb.sv']},runs=results,physical=False,exact_hardware_replay=False,scope='Synthetic line193, four known tile names, fixed MMC3 bank,12 continuous CPU phases; actual PPU address generation/MMC3/service/READ16 with70ns model. Three memory phases. Control removes new normal hint only; old overlap logic retained. Not game-level or all-phase electrical proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='sources'}))
if __name__=='__main__':main()
