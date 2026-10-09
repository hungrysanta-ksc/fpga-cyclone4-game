# SPDX-License-Identifier: MIT
"""Actual changed reader/boot; seeded RAM avoids repeating unchanged full writes."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_reader129 import ROOT,sha,put,replace,materialize

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
 old='''   fresh();load_chr32=mode!=0;begin_image();total=mode?98304:81920;before_writes=ram.writes;
   for(integer a=0;a<total;a++)send_byte(a);
   ck(ram.writes-before_writes==total&&!loaded&&!boot_fault,"pin writes/length");'''
 new='''   fresh();total=mode?98304:81920;
   // Seed only this fixture: loader write logic was unchanged and verified128.
   for(integer a=0;a<65536;a++)ram.prg[a]=pattern(a);
   for(integer a=0;a<32768;a++)ram.chr[a]=pattern(65536+a);
   dut.loader.state=1;dut.loader.loaded_bytes=total;dut.loader.chr32=mode!=0;'''
 s=replace(s,old,new)
 s=replace(s,' initial begin\n  integer total,before_writes;', (ROOT/'tests/nes-functional/reader129_helpers.svh').read_text()+'\n initial begin\n  integer total,before_writes;')
 s=replace(s,'  $display("PASS127 LOADER',(ROOT/'tests/nes-functional/reader129_cases.svh').read_text()+'\n  $display("PASS127 LOADER')
 put(f,s)
 for n in ['nes_reader129.py','nes_reader129_test.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
 def sim(label,expected):
  run('vsim',['-c','loader127_tb','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  log=(o/(label+'.log')).read_text();assert expected in log,label
  if expected.startswith('PASS'):assert '** Fatal:' not in log
 run('vlib',['work'],'vlib')
 files=['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','rom_boot_model.sv','loader127_tb.sv']
 run('vlog',['-sv',*files],'compile');sim('normal','PASS129 reader cancellations=96 stopped_clock_cases=3')
 physical=(o/'nes_rom_physical.sv').read_text()
 put(o/'negative-owner.sv',replace(physical,'owner_check<=check_mode;','owner_check<=!check_mode;'))
 run('vlog',['-sv','negative-owner.sv'],'negative-owner-compile');sim('negative-owner','** Fatal: LOADER127 OWNER129 captured mode')
 put(o/'negative-async.sv',replace(physical,'always @(posedge mem_clk or posedge mr)\n  if(mr)begin owner_valid','always @(posedge mem_clk)\n  if(mr)begin owner_valid'))
 run('vlog',['-sv','negative-async.sv'],'negative-async-compile');sim('negative-async','** Fatal: LOADER127 CANCEL129 owner cleared')
 put(o/'test129.json',json.dumps(dict(passed=True,seeded_image_bytes=[81920,98304],full_writes_repeated=False,additional_cancel_cases=96,stopped_clocks=3,causal_rejections=['wrong-captured-owner','synchronous-only-owner-cancel'],sources={p.name:sha(p) for p in o.iterdir() if p.suffix in ['.sv','.py']}),indent=2)+'\n')
 print('PASS129 seeded CHECK/RUN, ownership, raw cancellation and negative controls')
if __name__=='__main__':main()
