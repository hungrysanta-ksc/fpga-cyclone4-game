# SPDX-License-Identifier: MIT
"""Bind the partial 407 loader/RTL experiments without full-path claims."""
import json
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha

d=BASE/'probes/nes-nrom407'; build=d/'build04'
manifest=json.loads((build/'manifest407.json').read_text())
for name,h in manifest['sources'].items():assert sha(build/name)==h,name
source=json.loads((d/'source04/result.json').read_text())
transfer=json.loads((d/'transfer01/result.json').read_text())
cleanup=json.loads((d/'cleanup01/result.json').read_text())
spi=json.loads((d/'spi02/result.json').read_text())
arm=json.loads((d/'arm01/result.json').read_text())
for item in (source,transfer,cleanup,spi,arm):assert item['passed']
for item in (source,transfer,cleanup):assert item['generated_loader']==manifest['sources']['nes_h1_stm32.c']
assert source['generated_verify']==manifest['sources']['nes_rom_verify.c']
assert spi['RTL']==manifest['sources']['nes_rom_spi.sv']
assert arm['sources']['candidate']==manifest['sources']['nes_h1_stm32.c']
assert arm['sources']['layout']==manifest['sources']['nes_nrom406.c']
old=json.loads((BASE/'probes/nes-nrom406/map-base01/result.json').read_text())
new=json.loads((d/'map01/result.json').read_text())
assert old['passed'] and new['passed'] and len(old['inputs'])==len(new['inputs'])==90
changed=[n for n in old['inputs'] if old['inputs'][n]!=new['inputs'][n]]
assert set(changed)=={'cart_nrom.sv','nes_rom_spi.sv'}
assert new['inputs']['nes_rom_spi.sv']==manifest['sources']['nes_rom_spi.sv']
assert new['inputs']['cart_nrom.sv']==manifest['sources']['cart_nrom.sv']
for val in ('18,178','13,557','8,029','185,824'):assert val in new['summary']
report={'passed':True,'profile':'fixed NROM16 horizontal CHR-ROM8 no PRG-RAM','FPGA_status_ID':120,
        'sources':manifest['sources'],'loader_sections_tested':['file prepass + padded write loop','sd_source + independent verification','cleanup STOP/base control'],
        'test_mode':'separate extracted actual generated C blocks with modeled file/SPI/PSRAM/ownership; not full function',
        'serial_RTL':'real SPI status78 and idle STOP pulse',
        'ARM_object_text_bytes':{'reference_loader':9124,'candidate_loader':9196,'new_layout_object':206},
        'ARM_object_bss_bytes':{'reference_loader':772,'candidate_loader':772,'new_layout_object':0},
        'ARM_static_stack_bytes':{'reference_menu_probe':1008,'candidate_menu_probe':1032,'reference_sd_source':32,'candidate_sd_source':40},
        'full_ARM_link_RAM_stack_IRQ_cycles':None,
        'whole_Lite_MAP':{'LE':18178,'comb':13557,'FF':8029,'RAM_bits':185824,'changed_sources':changed},
        'startup_wire_lower_bound_seconds':{'padded_payload_only':393216*8/2625000,
          'DATA_and_STATUS_frames_only':393216*16*8/2625000,'assumptions':'2.625MHz, two 8-byte transfers per padded byte; excludes all other work'},
        'actual_ARM_SPI_IRQ_ROM_time':None,'MMC4_MMC5_time_or_area':None,
        'full_227_function_run':False,'full_loader_FPGA_cosimulation':False,'actual_base_recovery':False,'FIT':False,'STA':False,'physical60fps':False,
        'pins':{'source_test':sha(d/'source04/result.json'),'transfer_test':sha(d/'transfer01/result.json'),
                'cleanup_test':sha(d/'cleanup01/result.json'),'spi_test':sha(d/'spi02/result.json'),
                'ARM_test':sha(d/'arm01/result.json'),'map_summary':sha(d/'map01/output_files/board.map.summary')}}
out=ROOT/'analysis/nrom407-verification.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:report[k] for k in ('passed','profile','whole_Lite_MAP','ARM_object_text_bytes','full_227_function_run','actual_base_recovery','FIT')},indent=2))
