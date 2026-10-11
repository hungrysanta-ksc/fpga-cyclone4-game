# SPDX-License-Identifier: MIT
"""Actual raw CPU/DMA qualification and captured-prefix PPU collision boundary."""
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
 shutil.copy2(ROOT/'tests/nes-functional/game159_eligibility_tb.sv',a.out/'game159_eligibility_tb.sv')
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
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'game159_eligibility_tb.sv'],'vlog')
 results=[]
 for phase in [0,3.5,5.5]:
  for control in [0,1]:
   label=f'phase-{phase}-control-{control}'
   s=run('vsim',['-c','work.eligibility159_tb',f'+PHASE={phase}',f'+CONTROL={control}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
   rows=[tuple(map(int,m)) for m in re.findall(r'CASE159 offset=(-?\d+) control=(\d+) failed=(\d+) error=(\d+) checked=(\d+) requests=(\d+) write_reads=(\d+)',s)]
   assert len(rows)==13 and 'DONE159' in s
   print(label,rows,flush=True)
   assert 'ELIGIBILITY159 48' in s and 'READ159 source=0 samples=6' in s and 'READ159 source=1 samples=6' in s
   assert [row[0] for row in rows]==list(range(-1,12))
   if not control:assert all(row[2]==0 and row[3]==0 and row[4]>=2 and row[6]==0 for row in rows),(label,rows)
   else:
    assert all(row[6]==1 for row in rows),(label,rows)
    assert rows[0][2:4]==(1,2) and any(row[2]==1 for row in rows[1:]),(label,rows)
   results.append(dict(phase_ns=phase,control=control,rows=rows,log_sha256=sha(a.out/(label+'.log'))))
 result=dict(passed=True,rom_sha256=ROM_SHA,sources={n:sha(a.out/n) for n in VHDL+SV+EXTRA+['game159_eligibility_tb.sv']},runs=results,physical=False,scope='CPU/DMA output buses and clock-divider phase driven; actual raw mux/cart_pre/cart_ce/MMC3/early qualification/read/sample wiring live. Actual PPU/service/READ16 with70ns model. Twelve write phases plus observed-prefix seeded cache/initial-ready reconstruction, three memory phases, old-eligibility causal control. No real CPU instruction/game execution or full DMA controller replay; exact earlier cache/reader history unproven.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS159 eligibility/collision/CPU-DMA samples')
if __name__=='__main__':main()
