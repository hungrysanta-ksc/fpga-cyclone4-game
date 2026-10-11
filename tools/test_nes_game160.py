# SPDX-License-Identifier: MIT
"""Live rendering-enable pipeline/latch boundary and preserved159 read qualification."""
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
 shutil.copy2(ROOT/'tests/nes-functional/game160_transition_tb.sv',a.out/'game160_transition_tb.sv')
 regression=(ROOT/'tests/nes-functional/game159_eligibility_tb.sv').read_text()
 old='wire rom_cpu_address_valid,rom_ppu_address_valid,rom_cpu_sample,game147_prefetch_hint;'
 assert regression.count(old)==1
 regression=regression.replace(old,old+'\nwire game160_restart_hint;')
 (a.out/'game159_eligibility_tb.sv').write_text(regression,encoding='utf8',newline='\n')
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
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'game160_transition_tb.sv','game159_eligibility_tb.sv'],'vlog')
 results=[];regression=[]
 for phase in [0,3.5,5.5]:
  for dot in [334,336]:
   for latch in [0,90]:
    for control in [0,1]:
     label=f'phase-{phase}-dot-{dot}-latch-{latch}-control-{control}'
     s=run('vsim',['-c','work.transition160_tb',f'+PHASE={phase}',f'+DOT={dot}',f'+LATCH={latch}',f'+CONTROL={control}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
     assert 'DONE160' in s
     m=re.search(r'CASE160 failed=(\d+) error=(\d+) checked=(\d+)',s);assert m
     failed,error,checked=map(int,m.groups());assert failed==control
     if not control:assert error==0 and checked>=1
     else:assert error==2
     results.append(dict(phase_ns=phase,dot=dot,latch=latch,control=control,failed=failed,error=error,checked=checked,log_sha256=sha(a.out/(label+'.log'))))
     print(label,'PASS',flush=True)
  for control in [0,1]:
   label=f'regression159-phase-{phase}-control-{control}'
   s=run('vsim',['-c','work.eligibility159_tb',f'+PHASE={phase}',f'+CONTROL={control}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
   rows=[tuple(map(int,m)) for m in re.findall(r'CASE159 offset=(-?\d+) control=(\d+) failed=(\d+) error=(\d+) checked=(\d+) requests=(\d+) write_reads=(\d+)',s)]
   assert len(rows)==13 and 'DONE159' in s
   assert 'ELIGIBILITY159 48' in s and 'READ159 source=0 samples=6' in s and 'READ159 source=1 samples=6' in s
   if not control:assert all(row[2]==0 and row[3]==0 and row[4]>=2 and row[6]==0 for row in rows)
   else:assert all(row[6]==1 for row in rows) and rows[0][2:4]==(1,2)
   regression.append(dict(phase_ns=phase,control=control,rows=rows,log_sha256=sha(a.out/(label+'.log'))))
 result=dict(passed=True,rom_sha256=ROM_SHA,sources={n:sha(a.out/n) for n in VHDL+SV+EXTRA+['game160_transition_tb.sv','game159_eligibility_tb.sv']},runs=results,regression159=regression,regression159_original_sha256=sha(ROOT/'tests/nes-functional/game159_eligibility_tb.sv'),physical=False,scope='Actual2001 register write/re_sr enable/ALE/latch/PPU/service/READ16 paths. Dot/scanline/name/scroll/CPU output bus driven and previous low latch seeded; not full instruction/game replay. Two target dots/two old latch values/three memory phases, paired preview-off controls. Original159 regression gets only new unused wire declaration; its constant enabled-render stimulus never asserts restart.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS160 12 restart cases/12 control failures and159 regression')
if __name__=='__main__':main()
