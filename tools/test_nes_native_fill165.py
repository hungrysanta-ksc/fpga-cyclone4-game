# SPDX-License-Identifier: MIT
"""Bounded fill interface with actual joined required sets and private CHR."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['core','chr','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 files=['src/nes/diagnostic/nes_native_fill165.sv','tests/nes-functional/native_fill165_tb.sv']
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name)
 shutil.copy2(a.chr,a.out/'chr.hex');rom=bytes(int(v,16) for v in a.chr.read_text().split());assert len(rom)==131072
 sets={}
 for frame in range(12,21):
  lines=(a.core/f'frame-{frame}.dump').read_text().splitlines();assert lines[0].startswith('H 1 00 ')
  required={int(q):int(v,16) for k,q,v in (s.split() for s in lines[1:]) if k=='6'}
  assert set(required)==set(range(8192));sets[frame]=required
  (a.out/f'required-{frame}.hex').write_text(''.join(f'{required[i]:x}\n' for i in range(8192)))
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
  return s
 run('vlib',['work'],'vlib');run('vlog',['-sv',*[Path(n).name for n in files]],'vlog');cases=[]
 for frame,mode in [(i,0) for i in range(12,21)]+[(12,m) for m in range(1,16)]:
  name=f'fill-{frame}-{mode}'
  s=run('vsim',['-c','work.native_fill165_tb',f'-gMODE={mode}',f'+REQUIRED=required-{frame}.hex',
   '+CHR=chr.hex',f'+OUTPUT={name}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],name)
  m=re.search(r'PASS FILL165 mode=(\d+) checks=(\d+) requests=(\d+) bytes=(\d+) cycles=(\d+)',s);assert m
  info=dict(frame=frame,mode=mode,checks=int(m[2]),requests=int(m[3]),bytes=int(m[4]),cycles=int(m[5]))
  if mode in (0,8,14,15):
   actual=[tuple(int(v,16) if i==3 else int(v) for i,v in enumerate(line.split())) for line in (a.out/(name+'.tsv')).read_text().splitlines()]
   expected=[(41,t,lane,rom[t*16+lane],kind) for t,kind in sorted(sets[frame].items()) if kind for lane in range(16)]
   assert actual==expected and info['bytes']==len(expected),(frame,mode)
  cases.append(info)
 result=dict(passed=True,cases=cases,public_sources={n:sha(ROOT/n) for n in files+['tools/test_nes_native_fill165.py']},
  source_core_result_sha256=sha(a.core/'result.json'),private_chr_sha256=sha(a.chr),
  scope='Actual joined required-set queries replayed through modeled lookup/granted-memory interfaces; exact ROM bytes and bounded faults. Not connected to actual PSRAM arbitration, no CPU/PPU deadline or throughput/host ACK proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
