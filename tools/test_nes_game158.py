# SPDX-License-Identifier: MIT
"""Short synthetic BG/CPU collision sweep through actual154/155 hardware RTL."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,ROM_SHA,VHDL,SV,EXTRA,sha


def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 assert sha(a.rom)==ROM_SHA;a.out.mkdir(parents=True)
 for n in VHDL+SV+EXTRA:
  dst=a.out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.prepared/n,dst)
 shutil.copy2(ROOT/'tests/nes-functional/game158_transition_tb.sv',a.out/'game158_transition_tb.sv')
 shutil.copy2(ROOT/'tests/nes-functional/game158_mapper_tb.sv',a.out/'game158_mapper_tb.sv')
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
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'game158_transition_tb.sv','game158_mapper_tb.sv'],'vlog')
 mapper=run('vsim',['-c','work.mapper158_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'mapper')
 assert 'PASS158 mapper lookup 536 commits' in mapper
 results=[]
 for phase in [0,3.5,5.5]:
  for control in [0,1]:
   label=f'phase-{phase}-control-{control}'
   s=run('vsim',['-c','work.transition158_tb',f'+PHASE={phase}',f'+CONTROL={control}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
   rows=[tuple(map(int,m)) for m in re.findall(r'CASE158 mode=(\d+) control=(\d+) failed=(\d+) error=(\d+) checked=(\d+) requests=(\d+)',s)]
   assert len(rows)==36 and 'DONE158' in s
   print(label,rows,flush=True)
   assert all(row[2]==(1 if control or row[0]==2 else 0) for row in rows),(label,rows)
   results.append(dict(phase_ns=phase,control=control,rows=rows,log_sha256=sha(a.out/(label+'.log'))))
 result=dict(passed=True,rom_sha256=ROM_SHA,sources={n:sha(a.out/n) for n in VHDL+SV+EXTRA+['game158_transition_tb.sv']},runs=results,physical=False,exact_hardware_replay=False,scope='Synthetic line193/dot8 late bank-data or invert commit, plus late logical PPU address change negative. Actual PPU/MMC3/service/READ16 with70ns model;12 prior CPU-read start offsets and3 memory phases. CPU write bus driven early, actual cart_pre/commit strobes at retained relative phase; no live CPU program. Control disables only pending-write prediction. Actual PPU bytes compared against exact private target CHR; early normal mapping unchanged. Not full-game/all-bank/all-phase electrical proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='sources'}))
if __name__=='__main__':main()
