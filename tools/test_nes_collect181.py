#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded actual fetch/raster/compact join; synthetic PPU interface, no ROM boot."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('baseline','out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True)
 pins=json.loads((ROOT/'analysis/minreject180-verification.json').read_bytes())['verification']['sources']
 old=['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_frame165.sv']
 new=['src/nes/video/'+n+'.sv' for n in ('nes_patch_rows181','nes_patch_capture181','nes_native_compact181','nes_native_raster181','nes_native_frame181')]+['tests/nes-functional/collect181_tb.sv']
 sources={}
 for n in old:
  assert sha(a.baseline/n)==pins[n],n
  shutil.copy2(a.baseline/n,a.out/n);sources['baseline/'+n]=sha(a.baseline/n)
 for n in new:
  shutil.copy2(ROOT/n,a.out/Path(n).name);sources[n]=sha(ROOT/n)
 def run(exe,args):
  with (a.out/(exe+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=(a.out/(exe+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-4000:]
  return text
 run('vlib',['work']);run('vlog',['-sv',*old,*[Path(n).name for n in new]])
 s=run('vsim',['-c','work.collect181_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
 m=re.search(r'PASS COLLECT181 cases=(\d+) pixels=(\d+) baseline_words=(\d+) recovered_cells=(\d+)',s);assert m
 result=dict(passed=True,cases=int(m[1]),exact_raw_pixels=int(m[2]),normal_baseline_words=int(m[3]),recovered_normal_cells=int(m[4]),sources=sources,
  runner_sha256=sha(Path(__file__)),live_ppu=False,hardware=False,fit=False,
  scope='Actual180 fetch and candidate181 compact/raster/pixel join on synthetic post-CE interface; no actual PPU/game/MCU/wire/SNES integration.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(m[0])
if __name__=='__main__':main()
