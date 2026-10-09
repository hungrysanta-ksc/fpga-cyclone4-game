# SPDX-License-Identifier: MIT
"""Scoped127 actual loader pins, CHECK/RUN decoder, scaled guard and causal controls."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_loader127 import ROOT,sha,put,materialize
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin','baseline']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert not o.exists() and str(o).isascii()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 o.mkdir();materialize(o,a.baseline/'nes-control126/evidence',a.baseline/'nes-clock086/evidence')
 for n in ['loader127_tb.sv','guard127_tb.sv','spi_readback_control_tb.sv','rom_boot_model.sv']:
  shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 f=o/'rom_boot_model.sv';put(f,f.read_text().replace('assign #25','assign #70').replace('<35.70','<375.0'))
 f=o/'spi_readback_control_tb.sv';put(f,f.read_text().replace('#5.952381','#2.976'))
 for n in ['nes_loader127.py','nes_loader127_test.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 m=dict(candidate='NES-LOADER-127',passed=False,cases=[],scope='actual pin loader/boot+synthetic70ns RAM; actual SPI decoder+16-byte responder model; scaled guard; not full CPU/SPI/board session')
 def save():put(o/'result127.json',json.dumps(m,indent=2)+'\n')
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
 sim('loader127_tb','loader','PASS127 LOADER')
 sim('spi_readback_control_tb','decoder','PASS SPI CHECK CONTROL')
 sim('guard127_tb','guard','PASS127 GUARD')
 original=(o/'nes_rom_loader.sv').read_text();put(o/'negative-short-write.sv',original.replace('WRITE_CYCLES=64','WRITE_CYCLES=63'))
 run('vlog',['-sv','negative-short-write.sv'],'negative-write-compile');sim('loader127_tb','negative-write','** Fatal: WRITE pulse too short')
 original=(o/'nes_rom_spi.sv').read_text();needle='if(verified && loaded && !run_enable)start<=1;else fail(8);';assert needle in original
 put(o/'negative-unverified.sv',original.replace(needle,'start<=1;'))
 run('vlog',['-sv','negative-unverified.sv'],'negative-run-compile');sim('spi_readback_control_tb','negative-run','** Fatal: CHECK CONTROL')
 original=(o/'nes_diag_clock_guard127.sv').read_text();assert original.count('mem_age==671')==1
 put(o/'negative-old-timeout.sv',original.replace('mem_age==671','mem_age==31'))
 run('vlog',['-sv','negative-old-timeout.sv'],'negative-guard-compile');sim('guard127_tb','negative-guard','** Fatal: GUARD127 normal startup')
 m.update(passed=True,sources={str(p.relative_to(o)):sha(p) for p in o.iterdir() if p.is_file() and p.suffix in ['.sv','.py']},installable=False,full_session=False)
 save();print('PASS127 loader/decoder/guard + three causal rejections')
if __name__=='__main__':main()
