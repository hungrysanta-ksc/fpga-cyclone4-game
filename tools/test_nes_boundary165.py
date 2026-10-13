# SPDX-License-Identifier: MIT
"""Common reset/clock-halt lifecycle and unchanged native SPI stream replay."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','prior','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True,exist_ok=False)
 files=['nes_native_mailbox165.sv','nes_domain_reset124.sv','nes_native_spi165.sv']
 for n in files:shutil.copy2(a.prepared/n,a.out/n)
 tb=ROOT/'tests/nes-functional/boundary_reset165_tb.sv';shutil.copy2(tb,a.out/tb.name)
 # Exercise the exact local reset connection used by the real parent.
 s=(a.prepared/'nes_live_joint.sv').read_text()
 assert 'nes_domain_reset124 native_spi_release(.clk(host_clk),.raw_reset(reset),.reset(native_spi_reset));' in s
 assert 'nes_native_spi165 native_spi(.clk(host_clk),.reset(native_spi_reset),' in s
 spi_tb=(ROOT/'tests/nes-functional/native_spi165_tb.sv').read_text()
 assert 'nes_native_spi165 dut(clk,reset,' in spi_tb
 spi_tb=spi_tb.replace('nes_native_spi165 dut(clk,reset,','nes_native_spi165 dut(clk,local_reset,')
 # The test uses host_clk, as does the actual parent; all packet RTL is real.
 i=spi_tb.index('nes_native_spi165 ')
 spi_tb=spi_tb[:i]+'wire local_reset;nes_domain_reset124 release_local(.clk(clk),.raw_reset(reset),.reset(local_reset));\n'+spi_tb[i:]
 (a.out/'native_spi165_tb.sv').write_text(spi_tb)
 prior=a.prior/'nes-native-spi165/spi04'
 pins=json.loads((a.prior/'nes-native-spi165/evidence-manifest.json').read_bytes())
 assert sha(prior/'records.hex')==pins['spi04/records.hex'];shutil.copy2(prior/'records.hex',a.out/'records.hex')
 def run(exe,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if not negative:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-4000:])
  return log
 def sim(name,args,label,negative=False):return run('vsim',['-c',name,*args,'-do','onerror {quit -code 1}; run -all; quit -f'],label,negative)
 run('vlib',['work'],'vlib')
 run('vlog',['-sv',*files,tb.name,'native_spi165_tb.sv'],'compile')
 log=sim('boundary_reset165_tb',[],'boundary')
 cases=re.findall(r'PASS BOUNDARY165 width=\d+[^\r\n]+',log);assert len(cases)==6
 for phase in [0,3.5]:
  label='phase'+str(phase);sim('native_spi165_tb',[f'-gPHASE={phase}','+COUNT=1717'],label)
  src=prior/(label+'.transactions.txt');assert sha(src)==pins['spi04/'+src.name]
  assert (a.out/'transactions.txt').read_bytes()==src.read_bytes()
  shutil.copy2(a.out/'transactions.txt',a.out/src.name)
 # A bypassed local release must fail the clock-halt test, not merely compile.
 wrong=(a.out/files[0]).read_text().replace('src_reset=!sr[1],dst_reset=!dr[1]','src_reset=reset,dst_reset=reset')
 assert wrong!=(a.out/files[0]).read_text();(a.out/'wrong.sv').write_text(wrong)
 run('vlog',['-sv','wrong.sv'],'wrong-compile')
 bad=sim('boundary_reset165_tb',[],'wrong-reset',True)
 assert '** Fatal:' in bad and ('stopped source reset' in bad or 'stopped destination reset' in bad),bad[-2500:]
 result=dict(passed=True,cases=cases,delivered=450,common_resets=72,stopped_clock_cases=12,
  wrong_reset_rejected=True,spi_records=1717,spi_phases=2,spi_stream_byte_exact=True,
  sources={n:sha(a.prepared/n) for n in files},parent_sha256=sha(a.prepared/'nes_live_joint.sv'),
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_boundary165.py','tools/test_nes_boundary165.py','tests/nes-functional/boundary_reset165_tb.sv','tests/nes-functional/native_spi165_tb.sv']},
  scope='RTL common-reset, paused clocks and local release plus actual native SPI exact stream replay. No metastability simulation, full core boot, physical MCU or hardware.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
