# SPDX-License-Identifier: MIT
"""Actual selected PPU RTL to raw-row RAM, with deterministic external VRAM."""
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
 old=['rtl/bus_savestates.vhd','rtl/regs_savestates.sv','rtl/ppu.sv']
 new=['src/nes/video/nes_patch_rows181.sv','src/nes/video/nes_patch_capture181.sv','tests/nes-functional/patch_ppu181_tb.sv']
 sources={}
 for n in old:
  assert sha(a.baseline/n)==pins[n],n
  dest=a.out/n;dest.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(a.baseline/n,dest);sources['baseline/'+n]=sha(dest)
 for n in new:
  shutil.copy2(ROOT/n,a.out/Path(n).name);sources[n]=sha(ROOT/n)
 def run(exe,args):
  with (a.out/(exe+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(exe+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4500:]
  return s
 run('vlib',['work']);run('vcom',['-2008',old[0]]);run('vlog',['-sv',*old[1:],*[Path(n).name for n in new]])
 s=run('vsim',['-c','work.patch_ppu181_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
 m=re.search(r'PASS PPU181 observed=(\d+) retained=(\d+) transitions=(\d+) blank=(\d+) resumed=(\d+)',s);assert m
 result=dict(passed=True,observed_pixels=int(m[1]),exact_retained_pixels=int(m[2]),color_transitions=int(m[3]),sources=sources,
  runner_sha256=sha(Path(__file__)),render_off_samples=int(m[4]),render_resumed_samples=int(m[5]),raw_rows_sha256=sha(a.out/'ppu-rows.txt'),live_ppu=True,live_game=False,hardware=False,
  scope='Unmodified selected180 PPU with deterministic external VRAM and actual PPUMASK writes. Independent falling-edge observer vs captured7 rows. No full game/fetch/mapper/MCU/SNES path.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(m[0])
if __name__=='__main__':main()
