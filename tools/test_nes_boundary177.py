# SPDX-License-Identifier: MIT
"""Exact control preservation plus real-clock-phase collector release checks."""
from pathlib import Path
import argparse,json,re,os,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_boundary177 import transform,CHANGED,FIELDS

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 m=json.loads((a.candidate/'preparation.json').read_bytes())
 for n,h in m['sources'].items():
  assert sha(a.candidate/n)==h and sha(a.baseline/n)==m['baseline'][n],n
  if n in CHANGED:assert (a.candidate/n).read_text()==transform(n,(a.baseline/n).read_text())
  else:assert h==m['baseline'][n],n
 # Replacing only one concatenation plus output-only assign/port leaves the
 # exporter sequential/control statements and all other RTL byte-identical.
 s=(a.candidate/'nes_native_export165.sv').read_text()
 s=s.replace(' output wire [3:0] observe_state177,\n','').replace(' assign observe_state177=state;\n','')
 assert s==(a.baseline/'nes_native_export165.sv').read_text()
 for n in ['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_frame165.sv']:
  shutil.copy2(a.candidate/n,a.out/n)
 tb='tests/nes-functional/native_release177_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
 logs={};text=''
 for exe,args,label in [('vlib',['work'],'vlib'),('vlog',['-sv',*[p.name for p in a.out.glob('*.sv')]],'vlog'),
   ('vsim',['-c','work.native_release177_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'release')]:
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  text=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-2500:]
  logs[label]=sha(a.out/(label+'.log'))
 assert 'PASS RELEASE177 cases=14 checks=42' in text
 cases=[dict(zip(['case','phase','wait_ticks','generation'],map(int,m))) for m in re.findall(r'RELEASE177 case=(\d+) phase=(\d+) wait_ticks=(\d+) generation=(\d+)',text)]
 result=dict(passed=True,release_cases=cases,control_text_unchanged=True,changed=CHANGED,sources=m['sources'],
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_boundary177.py','tools/test_nes_boundary177.py',tb]},logs=logs,
  scope='Synthetic legal BG at full341-dot/262-line cadence;14 consumer release phases around scrub/start/raster/end. No physical PSRAM/SPI/SNES/game or root-cause proof; observer has no control feedback.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS BOUNDARY177 control-preserved release14')
if __name__=='__main__':main()
