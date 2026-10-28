# SPDX-License-Identifier: MIT
"""Prepare actual run136/observer/screen SPI prefix fixture; compile only.

It is intentionally not a full board or display implementation. The existing
411 simulation occupies the sole Starter seat; this job does not run vsim.
"""
import argparse
import sys
from pathlib import Path
from nes_delta231 import BASE,ROOT
p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
loader=(a.fixture/'run03-loader.c').resolve();disk=(a.fixture/'loader01-disk.c').resolve();assert loader.is_file() and disk.is_file()
runner=(ROOT/'tools/test_nes_nrom410_prefix.py').read_text()
def once(s,old,new):
 assert s.count(old)==1,(old,s.count(old));return s.replace(old,new)
runner=once(runner," and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'",'')
runner=once(runner,"(ROOT/'tests/nes-nrom408/full_tb.c').read_text()",'Path('+repr(str(loader))+').read_text()')
runner=once(runner,"str(ROOT/'tests/nes-nrom408/fat_disk.c')",'str(Path('+repr(str(disk))+'))')
runner=once(runner,"for f in host.glob('*.h'):shutil.copyfile(f,d/f.name)","for f in host.glob('*.h'):shutil.copyfile(f,d/f.name)\nshutil.copyfile(prod/'nes_run136.h',d/'nes_run136.h')")
replacement=r'''bench=(ROOT/'tests/nes-nrom410/prefix_tb.sv').read_text()
bench=bench.replace('wire fault;wire [3:0] error_code;wire spi_miso;', 'wire fault;wire [3:0] error_code;wire spi_miso,boot_miso,boot_selected,observer_miso,observer_selected,status_miso,status_selected;')
bench=bench.replace('nes_rom_spi_check dut(.*,.spi_selected());', """nes_rom_spi_check dut(.*,.spi_miso(boot_miso),.spi_selected(boot_selected));
 nes_run_observer134 observer(.clk(clk),.reset(reset),.core_reset(!run_enable),.cpu_sample(run_enable),.rom_fault(1'b0),
 .history_sample157(96'd0),.history_enable180(1'b0),.pad_event(1'b0),.pad_buttons(8'd0),.rom_error(4'd0),
 .ppu_fault_state154(64'd0),.fault_trigger(1'b0),.fault_context(64'd0),
 .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.selected(observer_selected),.miso(observer_miso));
 nes_screen_status151 status(.clk(clk),.reset(reset),.active(run_enable),.address(24'd0),.read_n(1'b1),.write_n(1'b1),.romsel_n(1'b1),.data_in(8'd0),
 .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.receive_write(),.selected(status_selected),.miso(status_miso));
 assign spi_miso=boot_selected&&!observer_selected&&!status_selected?boot_miso:
                 observer_selected&&!boot_selected&&!status_selected?observer_miso:
                 status_selected&&!boot_selected&&!observer_selected?status_miso:1'bz;
 always @(negedge mem_clk)if(!reset && ((boot_selected&&observer_selected)||(boot_selected&&status_selected)||(observer_selected&&status_selected)))$fatal(1,\"SPI owner collision\");""")
(d/'prefix_tb.sv').write_text(bench,newline='\n')
for n in ('nes_run_observer134.sv','nes_pad_trace156.sv','nes_ppu_history157.sv','nes_screen_status151.sv'):shutil.copyfile(board/n,d/n)'''
runner=once(runner,"shutil.copyfile(ROOT/'tests/nes-nrom410/prefix_tb.sv',d/'prefix_tb.sv')",replacement)
runner=once(runner,"'nes_rom_physical.sv','prefix_tb.sv'", "'nes_rom_physical.sv','nes_run_observer134.sv','nes_pad_trace156.sv','nes_ppu_history157.sv','nes_screen_status151.sv','prefix_tb.sv'")
runner=once(runner,'for label,cmd in steps:', 'for label,cmd in steps[:3]:')
runner=once(runner,"log=(d/'simulation.log').read_text(errors='replace')", "print('NROM415 DLL AND RTL COMPILE ONLY');raise SystemExit(0)\nlog=(d/'simulation.log').read_text(errors='replace')")
sys.argv=['test_nes_nrom410_prefix.py','--build',str(a.build),'--out',str(a.out),'--limit','256']
exec(compile(runner,str(ROOT/'tools/test_nes_nrom410_prefix.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom410_prefix.py')})
