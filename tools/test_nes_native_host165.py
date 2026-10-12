# SPDX-License-Identifier: MIT
"""Replay sealed actual-game scenes through exporter/fill/dual-clock host link."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha,VHDL,SV,EXTRA
from nes_native_host165 import prepare,FILES

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','scenes','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 inputs=prepare(a.evidence,a.out)
 baseline=json.loads((ROOT/'analysis/native-memory165-verification.json').read_bytes())
 assert sha(a.scenes/'result.json')==baseline['raw_result_sha256']['memory01']
 tb='tests/nes-functional/native_host165_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
 shutil.copy2(a.scenes/'chr.hex',a.out/'chr.hex')
 for frame in [12,14,16,18,20]:shutil.copy2(a.scenes/f'frame-{frame}.dump',a.out/f'frame-{frame}.dump')
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*FILES,'nes_native_ciram165.sv',Path(tb).name],'vlog')
 cases=[]
 for frame,mode,phase in [(12,0,0),(14,0,1.7),(16,0,4.2),(18,0,7.8),(20,0,10.1)]+[(12,m,3.5) for m in range(1,7)]:
  name=f'frame{frame}-mode{mode}';s=run('vsim',['-c','work.native_host165_tb',f'-gMODE={mode}',f'-gHOST_PHASE={phase}',f'+PREFIX=frame-{frame}','-do','onerror {quit -code 1}; run -all; quit -f'],name)
  m=re.search(r'PASS HOST165 mode=(\d+) commits=(\d+) aborts=(\d+) records=(\d+) bytes=(\d+)',s);assert m
  shutil.copy2(a.out/'records.tsv',a.out/(name+'.tsv'))
  cases.append(dict(frame=frame,mode=mode,phase_ns=phase,commits=int(m[2]),aborts=int(m[3]),records=int(m[4]),bytes=int(m[5]),stream_sha256=sha(a.out/(name+'.tsv'))))
 sources=['tools/test_nes_native_host165.py','tools/nes_native_host165.py',tb]+['src/nes/diagnostic/'+n for n in FILES]
 result=dict(passed=True,cases=cases,inputs=inputs,public_sources={n:sha(ROOT/n) for n in sources},baseline_result_sha256=sha(a.scenes/'result.json'),generated_joint_sha256=sha(a.out/'nes_live_joint.sv'),
 scope='Actual sealed-scene replay, actual fill and export RTL with modeled ROM backend; independent NES/host clocks and backpressure. Parent joint compiled only. No new core boot, SPI/MMIO endpoint, MCU/SNES runtime, fit or board.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS host link: '+str(len(cases))+' cases')
if __name__=='__main__':main()
