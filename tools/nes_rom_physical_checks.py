# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,sys
from nes_ncr1_live import ROOT,put,sha

def main():
 sys.argv.pop(1);p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--delay',type=int,default=3);a=p.parse_args()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 for n in ('src/nes/nes_rom_physical.sv','tests/nes-functional/rom_physical_model.sv','tests/nes-functional/rom_physical_tb.sv'):shutil.copy2(ROOT/n,out/Path(n).name)
 sources={p.name:sha(p) for p in out.iterdir()}
 def run(tool,args,name):
  with (out/(name+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,name
 run('vlib',['work'],'vlib');files=['nes_rom_physical.sv','rom_physical_model.sv','rom_physical_tb.sv']
 run('vlog',['-sv',*files],'vlog');cases=[]
 result=dict(candidate='NES-R1-ROM-PHYSICAL-052',passed=False,cases=cases,sources=sources)
 def save():put(out/'result.json',json.dumps(result,indent=2)+'\n')
 save()
 for phase in range(0,12000,750):
  name='phase-'+str(phase)
  run('vsim',['-c','rom_physical_tb','+PHASE_PS='+str(phase),'-do','onerror {quit -code 1}; run -all; quit -f'],name)
  log=(out/(name+'.log')).read_text();m=re.search(r'PASS PHYSICAL checks=(\d+) accepted=(\d+) completed=(\d+) canceled=(\d+) pins=(\d+) latency=(\d+)..(\d+) phase_ps=(\d+)',log)
  assert m and not re.search(r'\*\* (?:Fatal|Error):',log),'Inspect '+name
  cases.append(dict(zip(['checks','accepted','completed','canceled','pins','min_clocks','max_clocks','phase_ps'],map(int,m.groups()))));save()
 run('vlog',['-sv','+define+LATE_MEMORY',*files],'late-vlog')
 run('vsim',['-c','rom_physical_tb','+PHASE_PS=3500','-do','onerror {quit -code 1}; run -all; quit -f'],'late-memory')
 log=(out/'late-memory.log').read_text();assert '** Fatal: PHYSICAL check' in log and 'PASS PHYSICAL' not in log
 result.update(passed=True,late_memory_expected_failure=True,read_clocks=3,memory_period_ns=11.904762,nes_period_ns=46.560846,normal_access_ns=25,late_access_ns=60);save();print(json.dumps(result,indent=2))
if __name__=='__main__':main()
