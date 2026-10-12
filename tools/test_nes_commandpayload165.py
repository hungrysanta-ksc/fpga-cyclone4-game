# SPDX-License-Identifier: MIT
"""Latency-aware transaction comparison and cancellation at both queued stages."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_commandpayload165 import transform
from test_nes_balancedlength165 import bench as old_bench

from test_nes_commandstage165 import bench as stage_bench,connected

def bench():
 s=stage_bench()
 a='if(dut.load_data!==refdut.load_data)'
 assert s.count(a)==2
 return s.replace(a,'if(dut.load_valid && dut.load_data!==refdut.load_data)')

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.prepared/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.prepared/n).read_bytes())
 (a.out/'capture_tb.sv').write_text(bench());(a.out/'tag165_tb.sv').write_text(connected())
 def run(tool,args,label,expected=None):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if expected:assert expected in log and 'PASS COMMANDSTAGE165' not in log,(label,log[-2500:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2500:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','capture_tb.sv','tag165_tb.sv'],'compile')
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',sim('check165_tb'),'capture');assert 'PASS COMMANDSTAGE165 captures=393741 boundaries=120' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 needle='(captured || pending) && !ss_sync[1]';assert new.count(needle)==1
 (a.out/'wrong-overlap.sv').write_text(new.replace(needle,'pending && !ss_sync[1]'))
 run('vlog',['-sv','wrong-overlap.sv'],'negative-compile');run('vsim',sim('check165_tb'),'negative','STAGE165 cancelled command escaped')
 names=['tools/nes_commandpayload165.py','tools/test_nes_commandpayload165.py','tools/nes_commandstage165.py','tools/test_nes_commandstage165.py','tools/test_nes_balancedlength165.py','tools/test_nes_stopclear165.py','tools/test_nes_predecode165.py','tools/test_nes_check165.py','tests/nes-functional/tag165_tb.sv']
 result=dict(passed=True,captures=393741,boundaries=120,added_mem_cycles=1,transaction_result_comparison=True,same_edge_equivalence=False,wrong_overlap_rejected=True,sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.prepared/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),public_sources={n:sha(ROOT/n) for n in names})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
