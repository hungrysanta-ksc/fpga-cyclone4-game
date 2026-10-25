# SPDX-License-Identifier: MIT
"""Query/STOP drain/NES cursor boundary: independent of unchanged338 whole RTL."""
import argparse,json,shutil,subprocess,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--map',action='store_true');a=ap.parse_args();d=a.out.resolve();assert str(d).isascii() and not d.exists();d.mkdir(parents=True)
 files=[ROOT/'tools/nes_query355.sv',BASE/'probes/nes-boundary353/fixed01/nes_native_mailbox206.sv']
 if not a.map:files.append(ROOT/'tools/nes_query355_tb.sv')
 pins={}
 for f in files:shutil.copyfile(f,d/f.name);pins[f.name]=sha(d/f.name)
 def run(cmd,label):
  with (d/(label+'.log')).open('wb') as log:r=subprocess.run(cmd,cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(d/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal)',text),text[-5000:];return text
 if a.map:
  (d/'query.qpf').write_text('PROJECT_REVISION = "query"\n')
  (d/'query.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_query355','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2']+['set_global_assignment -name SYSTEMVERILOG_FILE '+f.name for f in files])+'\n')
  run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','query'],'map')
  summary=(d/'output_files/query.map.summary').read_text();report=(d/'output_files/query.map.rpt').read_text()
  result=dict(passed=True,pins=pins,summary=summary,warnings=[l.strip() for l in report.splitlines() if 'Warning' in l],scope='Standalone boundary cost, not additive whole-board MAP saving. No source/host control deleted. No FIT/STA.')
 else:
  q=Path('C:/altera_standard/25.1std/questa_fse/win64')
  run([str(q/'vlib.exe'),'work'],'vlib');run([str(q/'vlog.exe'),'-sv',*[f.name for f in files]],'vlog')
  rows=[]
  for i,phase in enumerate((0,3.1,11.8)):
   log=run([str(q/'vsim.exe'),'-c','-voptargs=+acc',f'-gPHASE={phase}','nes_query355_tb','-do','run -all; quit -f'],f'phase{i}')
   m=re.search(r'PASS QUERY355 phase=([0-9.]+) cases=(\d+) queries=(\d+) consumed=(\d+)',log);assert m,log[-3000:]
   lat=[int(x) for x in re.findall(r'READY_LATENCY ns=(\d+)',log)]
   rows.append(dict(phase=phase,cases=int(m[2]),queries=int(m[3]),consumed=int(m[4]),ready_latency_ps=lat))
  result=dict(passed=True,pins=pins,rows=rows,scope='Standalone dual-clock boundary, synthetic one-outstanding collector with held responses, STOP offset sweep and paused clocks. Not integrated source execution or CDC STA.')
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
