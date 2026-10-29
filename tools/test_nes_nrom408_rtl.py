# SPDX-License-Identifier: MIT
"""Actual 407 SPI with 227 boot/loader/PSRAM model; seeded READY, not full load."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.build=a.build.resolve();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
d.mkdir(parents=True)
ref=BASE/'probes/nes-counter224/test04'; board=BASE/'probes/nes-repeat227/asm02'
original=(board/'nes_rom_spi.sv').read_text();candidate=(a.build/'nes_rom_spi.sv').read_text()
assert original.replace("8'h74,flags","8'h78,flags")==candidate
(d/'candidate.sv').write_text(candidate,newline='\n')
(d/'reference.sv').write_text(candidate.replace('module nes_rom_spi_check(','module baseline_check165(',1),newline='\n')
bench=(ref/'connected_tb.sv').read_text();assert bench.count("wire_rx[55:48]!==8'h74")==1
bench=bench.replace("wire_rx[55:48]!==8'h74","wire_rx[55:48]!==8'h78")
anchor='.check_response_address(check_response_address),.check_data(check_data),.spi_miso(ref_miso));'
assert bench.count(anchor)==1
bench=bench.replace(anchor,anchor[:-2]+',.spi_selected(),.load_begin(),.load_chr32(),.load_valid(),.load_end(),.start(),.stop(),.load_data(),.fault(),.error_code(),.check_enable(),.check_request(),.check_address());')
anchor='  $display("PASS COMMIT167 wire_bits=%0d",compared_bits);'
assert bench.count(anchor)==1
bench=bench.replace(anchor,'''  // Seeded READY/count; check actual command interlocks and RUN/STOP.
  fresh();frame(8'h63,24'h60000,0);repeat(30)tick();
  if(!fault || run_enable)$fatal(1,"unverified START was accepted");
  fresh();dut.verified=1;refdut.verified=1;repeat(4)tick();
  frame(8'h63,24'h60000,0);repeat(30)tick();
  if(fault || !run_enable)$fatal(1,"verified START failed");
  frame(8'h64,24'h60000,0);repeat(30)tick();
  if(fault || run_enable || !loaded || dut.verified)$fatal(1,"RUN STOP failed");
  $display("PASS NROM408 seeded START interlock and RUN STOP");
'''+anchor)
(d/'connected_tb.sv').write_text(bench,newline='\n')
for n in ('nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv'):shutil.copyfile(board/n,d/n)
exe=Path('C:/altera_standard/25.1std/questa_fse/win64')
for label,tool,args in [('vlib','vlib',['work']),('vlog','vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','connected_tb.sv']),
                        ('simulation','vsim',['-c','work.tag165_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
 with(d/(label+'.log')).open('wb') as f:r=subprocess.run([str(exe/(tool+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(label+'.log')).read_text(errors='replace')[-3000:]
log=(d/'simulation.log').read_text(errors='replace')
assert 'acks=7 corruptions=19 cancels=72 overlaps=2' in log and 'PASS NROM408 seeded START interlock and RUN STOP' in log and 'Errors: 0, Warnings: 0' in log
result={'passed':True,'SPI':sha(a.build/'nes_rom_spi.sv'),'testbench':sha(d/'connected_tb.sv'),
        'boot_loader_physical':{n:sha(board/n) for n in ('nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv')},
        'scope':'actual FPGA SPI/boot/loader/physical read with PSRAM model, read/ACK, seeded verified START and RUN STOP/fault/reset; READY/count/verified seeded, not full write, CRC or ARM cosimulation'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
