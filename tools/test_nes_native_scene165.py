# SPDX-License-Identifier: MIT
"""Actual memory/OAM boundaries with a synthetic frame schedule, not ROM boot."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,VHDL,SV,EXTRA,sha
from nes_native_tap165 import NEW as CACHE
from nes_native_raster165 import NEW as RASTER
from nes_native_scene165 import prepare,NEW
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 inputs=prepare(a.evidence,a.out)
 # Unmodified original logic, module identifiers renamed solely to coexist.
 original=(a.evidence/'asm/nes_local_memory.sv').read_text()
 (a.out/'local_ref.sv').write_text(original.replace('nes_local_memory','nes_local_memory_ref'))
 original=(a.evidence/'asm/rtl/ppu.sv').read_text();start=original.index('module OAMEval(');end=original.index('endmodule',start)+len('endmodule')
 (a.out/'oam_ref.sv').write_text('import regs_savestates::*;\n'+original[start:end].replace('module OAMEval(','module OAMEval_ref('))
 tb='tests/nes-functional/native_scene165_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*[Path(n).name for n in CACHE+RASTER+NEW],'local_ref.sv','oam_ref.sv',Path(tb).name],'vlog')
 s=run('vsim',['-c','work.native_scene165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'scene')
 m=re.search(r'PASS SCENE165 checks=(\d+) game_port_checks=(\d+) frames=(\d+) rejects=(\d+)',s);assert m
 files=CACHE+RASTER+NEW+[tb,'tools/nes_native_scene165.py','tools/test_nes_native_scene165.py','tools/nes_native_raster165.py','tools/nes_native_tap165.py','tools/nes_game147.py','tools/nes_functional.py']
 result=dict(passed=True,checks=int(m[1]),game_port_checks=int(m[2]),frames=int(m[3]),rejects=int(m[4]),inputs=inputs,
  public_sources={n:sha(ROOT/n) for n in files},generated_sources={n:sha(a.out/n) for n in SV+EXTRA+['nes_live_joint.sv','local_ref.sv','oam_ref.sv']},
  raw_log_sha256={n.name:sha(n) for n in a.out.glob('*.log')},warnings={n.name:len(re.findall(r'\*\* Warning:',n.read_text(errors='replace'))) for n in a.out.glob('*.log')},
  hardware=False,scope='Synthetic frames with actual modified local memory and actual OAMEval writes/attribute mask/seeded render-rise copy, original logic controls, and CHR/raster/memory common NES-domain lease. Joint compiled only. Not ROM execution, required CHR readiness, mapped SNES coordinates, host CDC, fit or hardware.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(m[0],flush=True)
if __name__=='__main__':main()
