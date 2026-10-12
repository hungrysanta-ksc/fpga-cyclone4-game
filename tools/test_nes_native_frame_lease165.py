# SPDX-License-Identifier: MIT
"""Common frame lifetime and unsupported raster effects, plus joint compile."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,VHDL,SV,EXTRA,sha
from nes_native_frame165 import prepare,FILES

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 inputs=prepare(a.evidence,a.out)
 fill='src/nes/diagnostic/nes_native_fill165.sv';shutil.copy2(ROOT/fill,a.out/Path(fill).name)
 tb='tests/nes-functional/native_frame_lease165_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-6000:]
  return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*FILES,'nes_native_ciram165.sv',Path(fill).name,Path(tb).name],'vlog')
 s=run('vsim',['-c','work.native_frame_lease165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'lease')
 m=re.search(r'PASS FRAMELEASE165 checks=(\d+) scenes=(\d+) rejects=(\d+)',s);assert m
 paths=[tb,fill,'tools/test_nes_native_frame_lease165.py','tools/nes_native_frame165.py']+['src/nes/diagnostic/'+n for n in FILES]
 result=dict(passed=True,checks=int(m[1]),scenes=int(m[2]),rejects=int(m[3]),inputs=inputs,
  public_sources={n:sha(ROOT/n) for n in paths},generated_joint_sha256=sha(a.out/'nes_live_joint.sv'),
  scope='Synthetic schedules without hierarchical state forcing, then direct frame-query to bounded-fill connection (33 tiles/528 modeled bytes). Parent joint compiled only. Actual-core test is separate; not physical PSRAM arbitration, host CDC or fit.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(m[0],flush=True)
if __name__=='__main__':main()
