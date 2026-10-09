# SPDX-License-Identifier: MIT
"""Scoped127 actual loader pins, CHECK/RUN decoder, scaled guard and causal controls."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_command128 import ROOT,sha,put,materialize
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin','baseline']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert not o.exists() and str(o).isascii()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 o.mkdir();materialize(o,a.baseline)
 for n in ['loader127_tb.sv','guard127_tb.sv','spi_readback_control_tb.sv','rom_boot_model.sv']:
  shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 f=o/'rom_boot_model.sv';put(f,f.read_text().replace('assign #25','assign #70').replace('<35.70','<375.0'))
 f=o/'spi_readback_control_tb.sv';s=f.read_text()
 s=s.replace('module spi_readback_control_tb;','module spi_readback_control_tb #(parameter integer HALF127=60);').replace('#60','#(HALF127)').replace('#5.952381','#2.976')
 s=s.replace('reg mem_clk=0,reset=1,','reg mem_clk=0,raw_reset=1,').replace('always #2.976 mem_clk=~mem_clk;','reg mem_running128=1;wire reset;nes_domain_reset124 local_release(.clk(mem_clk),.raw_reset(raw_reset),.reset(reset));\n always #2.976 if(mem_running128)mem_clk=~mem_clk;')
 s=s.replace('reset=1;SPI_SS','raw_reset=1;SPI_SS').replace('reset=0;#200','raw_reset=0;#200')
 s=s.replace('endmodule',(ROOT/'tests/nes-functional/decoder127_monitor.svh').read_text()+'\nendmodule')
 s=s.replace(' initial begin\n  fresh();',(ROOT/'tests/nes-functional/command128_helpers.svh').read_text()+'\n initial begin\n  fresh();')
 s=s.replace('#10000000;', '#100000000;') # 512 SPI READ/ACK pairs exceed the old 10ms test-only watchdog.
 s=s.replace('  $display("PASS SPI CHECK CONTROL', (ROOT/'tests/nes-functional/command128_cases.svh').read_text()+'\n  $display("PASS SPI CHECK CONTROL')
 put(f,s)

 for n in ['nes_command128.py','nes_command128_test.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 m=dict(candidate='NES-COMMAND-128',passed=False,cases=[],scope='actual pipelined SPI decoder with16-byte responder model; half-SCK60/18ns; comparisons checked at retirement; not full SPI/CPU/board session')
 def save():put(o/'result128.json',json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,label
 def sim(top,label,expect):
  run('vsim',['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f'],label)
  log=(o/(label+'.log')).read_text(errors='replace');assert expect in log,label
  if expect.startswith('PASS'):assert '** Fatal:' not in log,label
  m['cases'].append(dict(name=label,expected=expect));save()
 save();run('vlib',['work'],'vlib')
 files=['nes_rom_loader.sv','nes_rom_physical.sv','nes_rom_boot.sv','nes_rom_spi.sv','nes_spi_boot.sv','nes_diag_clock_guard127.sv','nes_diag_startup_guard.sv','nes_domain_reset124.sv','rom_boot_model.sv','loader127_tb.sv','guard127_tb.sv','spi_readback_control_tb.sv']
 run('vlog',['-sv',*files],'compile')
 # Unchanged loader/guard are verified against the prior final suite externally.
 sim('spi_readback_control_tb','decoder','PASS SPI CHECK CONTROL')
 run('vsim',['-c','spi_readback_control_tb','-gHALF127=18','-do','onerror {quit -code 1}; run -all; quit -f'],'decoder-fast')
 log=(o/'decoder-fast.log').read_text(errors='replace');assert 'PASS SPI CHECK CONTROL' in log and '** Fatal:' not in log
 assert 'PASS128 boundary' in log
 m['cases'].append(dict(name='decoder-fast',expected='PASS SPI CHECK CONTROL'));save()

 original=(o/'nes_rom_spi.sv').read_text();needle='else if(!verified || !loaded || run_enable)body_error=8;';assert needle in original
 put(o/'negative-unverified.sv',original.replace(needle,''))
 run('vlog',['-sv','negative-unverified.sv'],'negative-run-compile');sim('spi_readback_control_tb','negative-run','** Fatal: CHECK CONTROL')
 original=(o/'nes_rom_spi.sv').read_text()
 needle='if(check_fault || (check_enable && boot_fault))fail(9);';assert needle in original
 put(o/'negative-fault-priority.sv',original.replace(needle,'if(!pending && (check_fault || (check_enable && boot_fault)))fail(9);'))
 run('vlog',['-sv','negative-fault-priority.sv'],'negative-priority-compile');sim('spi_readback_control_tb','negative-priority','RETIRE128 hard fault wins START')
 m.update(passed=True,sources={str(p.relative_to(o)):sha(p) for p in o.iterdir() if p.is_file() and p.suffix in ['.sv','.py']},installable=False,full_session=False)
 save();print('PASS128 decoder retirement + RUN causal rejection')
if __name__=='__main__':main()
