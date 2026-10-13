# SPDX-License-Identifier: MIT
"""New explicit-state loader + local reader on the unchanged actual SPI path."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from test_nes_update165 import connected as prior_connected

def connected():
 s=prior_connected()
 assert s.count('boot.loader.state=4;')==1
 s=s.replace('boot.loader.state=4;',"boot.loader.phase=16'h0010;")
 marker='if($countones(dut.approved_pulse)>1)'
 return s.replace(marker,'if(!$onehot(boot.loader.phase))$fatal(1,"DIRECTSTATE165 onehot connected");\n  '+marker)

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin','spi-reference']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 prior=json.loads((a.baseline/'result.json').read_bytes())
 assert sha(a.prepared/'nes_rom_spi.sv')==sha(a.baseline/'nes_rom_spi.sv')==prior['joint_functional_test']['source_sha256']
 a.out.mkdir()
 assert sha(a.spi_reference)==prior['joint_functional_test']['reference_sha256']
 (a.out/'reference.sv').write_text(a.spi_reference.read_text().replace('module nes_rom_spi_check(','module baseline_check165(',1))
 for n in ['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.prepared/n).read_bytes())
 (a.out/'tag165_tb.sv').write_text(connected())
 def run(tool,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2500:])
  return log
 run('vlib',['work'],'vlib')
 run('vlog',['-sv','reference.sv','nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','tag165_tb.sv'],'compile')
 seq=run('vsim',['-c','tag165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'connected')
 assert 'PASS COMMANDSTAGE165 wire_frames=219 sck_hz=2625000 ss_gap_ns=2000' in seq
 summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0]
 assert 'edges=1125909 reads=100 acks=7 corruptions=19 cancels=72 overlaps=2' in summary
 result=dict(passed=True,sequential_summary=summary,sources={n:sha(a.prepared/n) for n in ['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']},spi_unit_reuse_sha256=sha(a.baseline/'result.json'),spi_unit_captures=393741,onehot_invariant_checked=True,public_sources={**prior['joint_functional_test']['public_sources'],**{n:sha(ROOT/n) for n in ['tools/nes_directstate165.py','tools/test_nes_directjoint165.py','tools/test_nes_update165.py']}})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
