# SPDX-License-Identifier: MIT
"""Changed loader counter: full80/96KiB pin writes, CHECK/RUN and cancellation."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_counter131 import ROOT,sha,put,replace,materialize

def main():
 p=argparse.ArgumentParser()
 for n in ['out','baseline','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists() and str(o).isascii();o.mkdir()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 materialize(o,a.baseline)
 e=a.baseline/'nes-command128/evidence';pins=json.loads((e/'manifest.json').read_bytes())['files']
 for n in ['loader127_tb.sv','rom_boot_model.sv']:
  src=e/'boot05'/n;assert sha(src)==pins['boot05/'+n];shutil.copy2(src,o/n)
 f=o/'loader127_tb.sv';s=f.read_text()
 s=replace(s,'always #22.727 clk=~clk;','reg source_running129=1,mem_running129=1;\n always #22.727 if(source_running129)clk=~clk;')
 s=replace(s,'always #2.976 mem_clk=~mem_clk;','always #2.976 if(mem_running129)mem_clk=~mem_clk;')
 # Keep the full write loop: the phase counter changed in131.
 s=replace(s,' initial begin\n  integer total,before_writes;', (ROOT/'tests/nes-functional/reader129_helpers.svh').read_text()+'\n initial begin\n  integer total,before_writes;')
 cases=(ROOT/'tests/nes-functional/reader129_cases.svh').read_text()
 # Both real image writes plus87 fault writes precede the seeded cancellation
 # cases. The inherited87-only expectation applied to the old seeded suite.
 cases=replace(cases,'ck(ram.writes==87,','ck(ram.writes==180311,')
 s=replace(s,'  $display("PASS127 LOADER',cases+'\n  $display("PASS127 LOADER')
 put(f,s)
 for n in ['nes_counter131.py','nes_counter131_test.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,label
 def sim(label,expected):
  run('vsim',['-c','loader127_tb','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  log=(o/(label+'.log')).read_text();assert expected in log,label
  if expected.startswith('PASS'):assert '** Fatal:' not in log
 run('vlib',['work'],'vlib')
 files=['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','rom_boot_model.sv','loader127_tb.sv']
 run('vlog',['-sv',*files],'compile');sim('normal','PASS129 reader cancellations=96 stopped_clock_cases=3')
 put(o/'test131.json',json.dumps(dict(passed=True,full_image_bytes=[81920,98304],full_writes_repeated=True,additional_cancel_cases=96,stopped_clocks=3,causal_rejections=[],sources={p.name:sha(p) for p in o.iterdir() if p.suffix in ['.sv','.py']}),indent=2)+'\n')
 print('PASS131 full80/96KiB writes, CHECK/RUN and cancellation; preload negative in differential job')
if __name__=='__main__':main()
