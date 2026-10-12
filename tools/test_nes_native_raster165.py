# SPDX-License-Identifier: MIT
"""Changed-boundary raster packet and actual PPU observation tests; no ROM boot."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,VHDL,SV,EXTRA,sha
from nes_native_tap165 import NEW as CACHE
from nes_native_raster165 import prepare,NEW

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 inputs=prepare(a.evidence,a.out)
 tb='tests/nes-functional/native_raster165_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:]
  return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*[Path(n).name for n in CACHE+NEW],Path(tb).name],'vlog')
 s=run('vsim',['-c','work.native_raster165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'raster')
 m=re.search(r'PASS RASTER165 checks=(\d+) frames=(\d+) rejections=(\d+)',s);assert m
 files=CACHE+NEW+[tb,'tools/nes_native_raster165.py','tools/test_nes_native_raster165.py','tools/nes_native_tap165.py','tools/nes_game147.py','tools/nes_functional.py']
 result=dict(passed=True,checks=int(m[1]),frames=int(m[2]),rejections=int(m[3]),inputs=inputs,
  public_sources={n:sha(ROOT/n) for n in files},
  generated_sources={n:sha(a.out/n) for n in SV+EXTRA+['nes_live_joint.sv']},
  raw_log_sha256={n.name:sha(n) for n in a.out.glob('*.log')},
  warnings={n.name:len(re.findall(r'\*\* Warning:',n.read_text(errors='replace'))) for n in a.out.glob('*.log')},
  hardware=False,scope='Synthetic 224-row packets, actual PaletteRam writes/aliases/corruption, seeded actual PPU observation and delayed scroll effects. Core/probe/joint compiled, not a ROM execution or board run. No OAM/maps/CHR required set, combined generation, host CDC, synthesis or SNES consumer.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(m[0],flush=True)
if __name__=='__main__':main()
