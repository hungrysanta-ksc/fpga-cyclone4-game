# SPDX-License-Identifier: MIT
"""Compare tested C with final ARM and check real call sites; no hardware claim."""
from pathlib import Path
import argparse,json,re
from nes_mcu_loader import sha
from nes_diag_recovery_checks import function

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--host',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 src=a.arm/'src';names=['nes_cf86_session094.c','nes_cf86_session094.h','nes_h1_stm32.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c','nes_diag_runtime.c','nes_diag_runtime.h','nes_h1_session.c']
 for n in names:assert sha(src/n)==sha(a.host/n),n
 # Host model uses065 return module; ARM retains076 whitelist. Only shared
 # state/guard functions used by this suite must match exactly.
 guards=['nes_return_reset','nes_return_fail','nes_return_failed','nes_return_log_allow','nes_return_log_allowed','nes_return_io_begin','nes_return_io_step']
 for n in guards:assert function((src/'nes_menu_return.c').read_text(),n)==function((a.host/'nes_menu_return.c').read_text(),n),n
 for n in ['stm32f4xx/sdnative.c','stm32f4xx/spi.c','stm32f4xx/timer.c','memory.c','ff.c','nes_menu_return.c','nes_menu076.c','main.c']:
  assert sha(src/n)==sha(a.baseline/n),n
 old=(a.baseline/'nes_h1_stm32.c').read_text();new=(src/'nes_h1_stm32.c').read_text();prefix=old[:old.index('bool nes_menu_sd_probe(')]
 assert new.startswith(prefix)
 calls={'nes_rom_spi_transfer':['nes_cf86_check094'], 'cf86_short094':['nes_cf86_check094'], 'nes_rom_verify':['nes_cf86_monitoring094','nes_cf86_fail094'], 'nes_cf86_check094':['owner094','fpga_get_done','nes_cf86_fail094'], 'nes_cf86_arm094':['owner094','fpga_get_done','nes_cf86_fail094'], 'nes_cf86_fail094':['snes_reset','nes_return_fail'], 'nes_cf86_finish094':['nes_cf86_check094']}
 for fn,targets in calls.items():
  d=(a.arm/(fn+'-disassembly.txt')).read_text(encoding='utf-8-sig');assert re.search(r'<'+fn+r'(?:\.constprop\.\d+)?>:',d),fn
  for target in targets:assert re.search(r'\b(?:bl|b\.w)\s+[^\n]*<'+target+r'>',d),(fn,target)
 fw=src/'obj-nes-094/firmware.stm';elf=src/'obj-nes-094/sd2snes.elf'
 result=dict(candidate='NES-CF86-SESSION-094',firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),host_arm_identical={n:sha(src/n) for n in names},shared_guard_functions=guards,arm_calls=calls,actual_native077_retained=True,legacy_prefix_identical=True,physical=False,installable=False)
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(dict,list))}))
if __name__=='__main__':main()
