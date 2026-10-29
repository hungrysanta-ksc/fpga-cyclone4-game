# SPDX-License-Identifier: MIT
"""Check the selected480 RTL cartridge program bus, not local emulator ROM.

Uses live480 fixtures without its DPI/CPU adapter; --board recompiles the board.
Run inside the authorized FLOAT wrapper. Seeded loader/ROM, ideal clocks and
transaction pins: does not prove physical IO timing or execute a 65816.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--live', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--board', type=Path, help='Compile a new selected board instead of reusing480.')
p.add_argument('--bin', type=Path, default=Path('C:/altera_standard/25.1std/questa_fse/win64'))
a = p.parse_args()
live = a.live.resolve()
d = a.out.resolve()
assert not d.exists() and ((live/'work').is_dir() or a.board)
d.mkdir(parents=True)
for n in ['sink-program.hex', 'fixture-prg.hex', 'fixture-chr.hex']:
    shutil.copyfile(live/n, d/n)
s = (live/'join208_tb.sv').read_text(encoding='utf8')
s = s[:s.index(' import "DPI-C"')].replace('module nrom447_tb;', 'module mmc481_bootbus_tb;')
s += r'''
 reg [7:0] expected[0:4095];integer checked=0;
 task automatic read_byte(input [23:0] address,input [7:0] wanted,input integer phase);
  #(phase);SNES_ADDR_IN=address;SNES_ROMSEL_IN=0;
  #90.908;SNES_READ_IN=0;#180.816;
  if(SNES_DATABUS_OE||!SNES_DATABUS_DIR||SNES_DATA!==wanted)
   $fatal(1,"bootbus addr=%h wanted=%h actual=%h oe=%b dir=%b",address,wanted,SNES_DATA,SNES_DATABUS_OE,SNES_DATABUS_DIR);
  checked++;#1;SNES_READ_IN=1;#1;
  if(!SNES_DATABUS_OE||SNES_DATABUS_DIR)$fatal(1,"read release not immediate");
  SNES_ROMSEL_IN=1;SNES_ADDR_IN=24'h123456;#45.454;
 endtask
 initial begin
  $readmemh("sink-program.hex",expected);
  $readmemh("fixture-prg.hex",ram.prg,0,262143);
  $readmemh("fixture-chr.hex",ram.chr,0,131071);
  wait(!dut.core.diagnostic_reset);repeat(20)@(negedge dut.core.mem_clk);
  dut.core.loader_boot.boot.loader.phase=16'h10;
  dut.core.loader_boot.boot.loader.loaded_bytes=19'h60000;
  dut.core.loader_boot.boot.loader.count_complete=1;
  dut.core.loader_boot.control.verified=1;
  dut.core.loader_boot.content_lifetime.serial=1;
  repeat(8)@(negedge dut.core.mem_clk);command(8'h63,24'h60000);
  wait(!dut.core_reset);repeat(20)@(negedge dut.host_clk);
  // Reset-vector reads first, then every initialized byte and aliases/gaps.
  read_byte(24'h00fffc,expected[4092],0);
  read_byte(24'h00fffd,expected[4093],3);
  for(integer i=0;i<4032;i++)read_byte(24'h008000+24'(i),expected[i],i%23);
  for(integer i=0;i<64;i++)read_byte(24'h00ffc0+24'(i),expected[4032+i],i%23);
  read_byte(24'h008fc0,8'hff,7);read_byte(24'h00ffbf,8'hff,17);
  tx[0]=8'h73;for(integer i=1;i<8;i++)tx[i]=0;transfer(8);
  if(rx[1]!==8'he6||rx[2]!==0||rx[3]!==0||rx[4]!==7||rx[7]!==2)
   $fatal(1,"status does not observe actual bus reads %h %h %h %h %h",rx[1],rx[2],rx[3],rx[4],rx[7]);
  // Explicit manual milestone, never represented as CPU boot execution.
  snes_write(24'h007000,8'h31);transfer(8);
  if(rx[2]!==8'h31)$fatal(1,"manual milestone not received");
  command(8'h64,24'h60000);#1000;
  if(!dut.core_reset||dut.core.run_enable||!SNES_DATABUS_OE||dut.sink_fault||dut.rom_fault)
   $fatal(1,"STOP did not release the bus");
  $display("PASS MMC481 bootbus reads=%0d status_flags=7 manual_stage31 STOP",checked);$finish;
 end
 initial begin #5000000;$fatal(1,"bootbus watchdog");end
endmodule
'''
(d/'bootbus_tb.sv').write_text(s, encoding='utf8', newline='\n')
if a.board:
    assert (a.board/'sink-program.hex').read_bytes() == (live/'sink-program.hex').read_bytes()
    s = s.replace("rx[4]!==7||rx[7]!==2", "rx[4]!==8'hdf||rx[7]!==3")
    s = s.replace('status_flags=7 manual_stage31 STOP', 'status_flags=223 manual_stage31 STOP')
    s = s.replace("  tx[0]=8'h73;", "  SNES_ADDR_IN=24'h008000;SNES_ROMSEL_IN=0;SNES_READ_IN=0;#200;\n  tx[0]=8'h73;")
    s = s.replace('  // Explicit manual milestone,', "  SNES_READ_IN=1;SNES_ROMSEL_IN=1;SNES_ADDR_IN=24'h123456;#200;\n  // Explicit manual milestone,")
    s = s.replace('  // Reset-vector reads first,', '''  status_frame(8'h65,0);
  if(rx[1]!==8'h7a)$fatal(1,"MMC481 profile mismatch: %h",rx[1]);
  // Reset-vector reads first,''')
    (d/'bootbus_tb.sv').write_text(s, encoding='utf8', newline='\n')

def run(name, args):
    r = subprocess.run([str(a.bin/args[0]), *args[1:]], cwd=d,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (d/name).write_bytes(r.stdout)
    if r.returncode:
        raise RuntimeError(f'{name}: exit {r.returncode}; inspect raw log')

run('vmap-init.log', ['vmap.exe', '-c'])
run('vmap-live.log', ['vmap.exe', 'live480', str(live/'work')])
run('vlib.log', ['vlib.exe', 'work'])
if a.board:
    from nes_functional import VHDL
    for q in a.board.rglob('*'):
        if q.is_file() and q.suffix in ['.sv', '.v', '.vhd', '.vh', '.mif', '.hex', '.qsf', '.sdc', '.qip']:
            dest = d/q.relative_to(a.board)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(q, dest)
    for n in ['run133_pll_model.sv', 'rom_boot_model.sv']:
        shutil.copyfile(live/n, d/n)
    names = re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)', (d/'board.qsf').read_text(encoding='utf8'))
    for i, n in enumerate(VHDL):
        run(f'vcom-{i}.log', ['vcom.exe', '-2008', n])
    sv = [n for n in names if n not in VHDL and n != 'nes_clock_pll123.v']
    if 'nes_native_ciram165.sv' not in sv:
        sv.append('nes_native_ciram165.sv')
    run('compile.log', ['vlog.exe', '-sv', '-mfcu', *sv, 'run133_pll_model.sv', 'rom_boot_model.sv', 'bootbus_tb.sv'])
else:
    run('compile.log', ['vlog.exe', '-sv', 'bootbus_tb.sv'])
libs = [] if a.board else ['-L', 'live480']
run('simulation.log', ['vsim.exe', *libs, '-L', 'altera_mf_ver', '-c',
                       'work.mmc481_bootbus_tb', '-do', 'onerror {quit -code 1};run -all;quit -f'])
log = (d/'simulation.log').read_text(encoding='utf8')
assert f"PASS MMC481 bootbus reads=4100 status_flags={223 if a.board else 7} manual_stage31 STOP" in log
assert 'Errors: 0' in log
result = {'passed': True, 'reads': 4100,
          'board': '481 fresh compilation' if a.board else '480 reused compilation',
          'program_SHA256': hashlib.sha256(bytes.fromhex((d/'sink-program.hex').read_text(encoding='utf8'))).hexdigest(),
          'scope': __doc__, 'physical_timing': False, 'CPU_execution': False}
(d/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
print(json.dumps(result))
