# SPDX-License-Identifier: MIT
"""Actual RTL reset/induction proof: fault implies CHECK disabled on every edge."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_board204 import ROOT,BASE,sha
from nes_enable219 import transform
from test_nes_retire219 import bench,connected
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert str(a.out).isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-retire219';old=d/'source01/nes_spi_boot.sv';new=d/'source02/nes_spi_boot.sv'
 assert new.read_text()==transform(old.read_text())
 spi=(d/'source02/nes_rom_spi.sv').read_text();(a.out/'candidate.sv').write_text(spi)
 (a.out/'reference.sv').write_text(spi.replace('module nes_rom_spi_check(','module baseline_check165(',1))
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((d/'source02'/n).read_bytes())
 s=bench().replace('integer count=0,followups=0;','integer count=0,followups=0,invariant_checks=0;reg invariant_before;')
 needle='#1;mem_clk=1;#1;';assert s.count(needle)==2
 s=s.replace(needle,'''invariant_before=!(dut.fault && dut.check_enable);
 #1;mem_clk=1;#1;
 if(invariant_before || reset)begin
  if(dut.fault && dut.check_enable)$fatal(1,"ENABLE219 invariant");
  invariant_checks++;
 end''')
 s=s.replace('$finish;','$display("PASS ENABLE219 induction=%0d",invariant_checks);$finish;')
 (a.out/'state_tb.sv').write_text(s)
 seq=connected();assert '.check_enable(check_enable),.check_request(check_request)' in seq
 seq=seq.replace('   edges++;','   edges++;if(dut.fault && dut.check_enable)$fatal(1,"ENABLE219 wire invariant");')
 (a.out/'connected_tb.sv').write_text(seq)
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  t=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal: ENABLE219 invariant' in t,t[-2000:]
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-2000:]
  return t
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv'],'compile')
 t=run('vsim',sim('state181_tb'),'induction');checks=int(re.search(r'PASS ENABLE219 induction=(\d+)',t)[1]);assert checks>1000000
 wire=run('vsim',sim('tag165_tb'),'connected');assert 'wire_bits=14016' in wire and 'acks=7 corruptions=19 cancels=72 overlaps=2' in wire
 wrong=spi.replace('check_enable<=!state_error && state_enable;','check_enable<=state_enable;');assert wrong!=spi
 (a.out/'wrong.sv').write_text(wrong);run('vlog',['-sv','wrong.sv'],'negative-compile');run('vsim',sim('state181_tb'),'negative',True)
 r=dict(passed=True,induction_checks=checks,wire_summary=re.search(r'PASS TAG165[^\r\n]+',wire)[0],negative_missing_disable=True,
  scope='Reset and conditional invariant preservation over actual RTL transitions; arbitrary seeded fault=1/enable=1 is excluded. Real SPI fixture uses the same raw CHECK enable as new top. Read reset and RUN fault gates unchanged.',
  binding_source_pins={str(x.relative_to(BASE)):sha(x) for x in [old,new,d/'source02/nes_rom_spi.sv']},
  sources={x.name:sha(x) for x in a.out.glob('*.sv')},public_sources={n:sha(ROOT/n) for n in ['tools/nes_enable219.py','tools/test_nes_enable219.py','tools/test_nes_retire219.py']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['sources','public_sources','binding_source_pins']}))
if __name__=='__main__':main()
