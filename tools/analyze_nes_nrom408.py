# SPDX-License-Identifier: MIT
"""Bind whole-loader/FatFS, actual FPGA boundary and ARM link evidence."""
import json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

d=BASE/'probes/nes-nrom408';build=BASE/'probes/nes-nrom407/build04'
manifest=json.loads((build/'manifest407.json').read_text())
fat=json.loads((d/'fatfs02/result.json').read_text())
full=json.loads((d/'full04/result.json').read_text())
rtl=json.loads((d/'rtl03/result.json').read_text())
for r in (fat,full,rtl):assert r['passed']
assert fat['loader']==full['loader']==manifest['sources']['nes_h1_stm32.c']
assert fat['verify']==full['verify']==manifest['sources']['nes_rom_verify.c']
assert fat['FatFS_source']==sha(BASE/'probes/nes-repeat227/arm01/src/ff.c')
assert fat['test']==full['test']==sha(ROOT/'tests/nes-nrom408/full_tb.c')
assert fat['disk_test']==sha(ROOT/'tests/nes-nrom408/fat_disk.c')
assert rtl['SPI']==manifest['sources']['nes_rom_spi.sv']
for n in ('nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc','nes_nrom406.c','nes_nrom406.h','Makefile'):
 assert sha(d/'arm01/src'/n)==manifest['sources'][n],n
asm=(d/'arm01/menu-disasm.log').read_text(errors='replace')
assert all(s in asm for s in ('<nes_nrom406_header>','<nes_nrom406_layout>','<nes_rom_verify>'))
assert '<nes_nrom406_layout>' in (d/'arm01/source-disasm.log').read_text(errors='replace')
size=(d/'arm01/compare-size.log').read_text(errors='replace')
assert '199785' in size and '200061' in size and size.count('10040')==2 and size.count('18076')==2
assert (d/'arm01/src/obj-nes-100/firmware.stm').stat().st_size==210104
log=(d/'fatfs02/test.log').read_text(errors='replace')
assert all(f'NROM408 case={n} ' in log for n in range(9))
report={'passed':True,'profile':'fixed NROM16 horizontal CHR-ROM8, no PRG-RAM',
 'actual_227_loader_function':True,'actual_227_FatFS':True,'synthetic_FAT16_disk':True,
 'C_full_loader_peer':'modeled SPI/PSRAM, identify/run/base, not actual FPGA RTL',
 'C_cases':9,'C_success':'3 passes/CRC, checked START and modeled STOP/base/IRQ restore',
 'C_negative':'header, wrong ID, change during pass2/pass3, write/readback error, STOP/base failure; fail-closed',
 'actual_FPGA_RTL':'SPI/boot/loader/physical reader with modeled PSRAM; READY/count/verified seeded',
 'RTL_checks':'7 read ACKs, 19 corruptions, 72 cancellation phases, 2 overlap, unverified START rejection, verified RUN then STOP',
 'full_loader_FPGA_cosimulation':False,'actual_hardware_STOP_base_recovery':False,
 'linked_ARM':{'firmware_bytes_reference':209828,'firmware_bytes_candidate':210104,'delta':276,
               'text_reference':199785,'text_candidate':200061,'static_data':10040,'static_bss':18076,
               'same_conditions':True,'full_IRQ_stack_and_execution_time':None,'hardware_package':False},
 'whole_Lite_MAP':{'baseline_LE':18850,'candidate_LE':18178,'baseline_comb':13951,'candidate_comb':13557,
                   'FF':8029,'RAM_bits':185824,'scope':'227 board MAP, cart+SPI changed, actual full loader not connected'},
 'performance':{'candidate_A_B_full_time':None,'actual_ARM_IRQ_SPI_ROM_schedule':None,'MMC4_MMC5_contention':None},
 'FIT':False,'STA':False,'physical60fps':False,
 'pins':{'fatfs_test':sha(d/'fatfs02/result.json'),'RTL_test':sha(d/'rtl03/result.json'),
         'firmware':sha(d/'arm01/src/obj-nes-100/firmware.stm'),'ELF':sha(d/'arm01/src/obj-nes-100/sd2snes.elf'),
         'menu_disassembly':sha(d/'arm01/menu-disasm.log'),'map_summary':sha(BASE/'probes/nes-nrom407/map01/output_files/board.map.summary')}}
out=ROOT/'analysis/nrom408-verification.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:report[k] for k in ('passed','C_cases','full_loader_FPGA_cosimulation','linked_ARM','whole_Lite_MAP','performance')},indent=2))
