# SPDX-License-Identifier: MIT
"""Onehot loader differential, lookahead invariant, reset/drain and negatives."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_legality174 import transform
from test_nes_directloader165 import bench as previous

def bench():
 s=previous().replace('refdut.state=state;',"refdut.phase=16'b1<<state;")
 seed="dut.phase=16'b1<<state;"
 s=s.replace(seed,seed+'''dut.reject_state[0]=(state==1 || state==2 || state==3 || state==5 || state==7 || state==8);
 dut.reject_state[1]=(state==0 || state==1 || state==2 || state==3 || state==5 || state==7 || state==8);
 dut.reject_state[2]=(state==0 || state==2 || state==3 || state==4 || state==5 || state==7 || state==8);
 dut.reject_state[3]=(state==0 || state==4 || state==5);''')
 at=' if(!$onehot(dut.phase))'
 assert at in s
 s=s.replace(at,''' if(dut.reject_state!=={
  (dut.phase[0] || dut.phase[4] || dut.phase[5]),
  (dut.phase[0] || dut.phase[2] || dut.phase[3] || dut.phase[4] || dut.phase[5] || dut.phase[7] || dut.phase[8]),
  (dut.phase[0] || dut.phase[1] || dut.phase[2] || dut.phase[3] || dut.phase[5] || dut.phase[7] || dut.phase[8]),
  (dut.phase[1] || dut.phase[2] || dut.phase[3] || dut.phase[5] || dut.phase[7] || dut.phase[8])})$fatal(1,"LEGALITY174 lookahead invariant");
 if(!$onehot(dut.phase))''')
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True,exist_ok=False)
 old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.candidate/'nes_rom_loader.sv').read_text();assert new==transform(old)
 (a.out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #'))
 (a.out/'candidate.sv').write_text(new);(a.out/'bench.sv').write_text(bench())
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert re.search(r'\*\* Fatal: (DIFF131|LEGALITY174)',log) and 'PASS STATE165' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Fatal|Error):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','bench.sv'],'compile')
 args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',args,'equivalence');assert 'PASS STATE165 states=294912 sequences=1056' in log
 for label,needle,wrong in [('lookahead','reject_state[3]<=to_idle || to_ready || to_run;','reject_state[3]<=phase[IDLE] || phase[READY] || phase[RUN];'),
  ('blocked','(!commands_blocked && (illegal_begin','(1\'b1 && (illegal_begin'),
  ('stop','wire illegal_data=load_valid && !stop','wire illegal_data=load_valid')]:
  assert new.count(needle)==1;(a.out/(label+'.sv')).write_text(new.replace(needle,wrong))
  run('vlog',['-sv',label+'.sv'],label+'-compile');run('vsim',args,label,True)
 r=dict(passed=True,states=294912,sequences=1056,invariant=True,negatives=['lookahead','blocked','stop'],source_sha256=sha(a.candidate/'nes_rom_loader.sv'),reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),bench_sha256=sha(a.out/'bench.sv'),scope=__doc__,
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_legality174.py','tools/test_nes_legality174.py','tools/test_nes_directloader165.py','tools/test_nes_state165.py','tools/test_nes_drain165.py','tests/nes-functional/counter131_diff_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS LEGALITY174 294912 states/1056 sequences/lookahead invariant/3 negatives')
if __name__=='__main__':main()
