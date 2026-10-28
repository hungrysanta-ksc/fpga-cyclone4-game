# SPDX-License-Identifier: MIT
"""Audit assembled diagnostic pair; never classify it as hardware ready."""
import json
from nes_delta231 import BASE,ROOT,sha
d=BASE/'probes/nes-nrom423/asm01';arm=BASE/'probes/nes-nrom418/arm01/src/obj-nes-100/firmware.stm'
enc=(d/'fpga_nrom16.bi3').read_bytes();rbf=(d/'board.rbf').read_bytes();out=bytearray();i=0
while i<len(enc):
 op=enc[i];i+=1
 if op==0x9b:
  assert i<len(enc);out.append(enc[i]);i+=1
 elif op in (0x5b,0x77):
  n=3 if op==0x77 else 2;assert i+n<=len(enc)
  value=enc[i];count=enc[i+1]+(enc[i+2]*256 if n==3 else 0);assert count>0
  out.extend(bytes([value])*count);i+=n
 else:out.append(op)
assert bytes(out)==rbf
rom=json.loads((BASE/'probes/nes-nrom423/nrom423-romcheck02/result.json').read_text());assert rom['passed'] and len(rom['checks'])==1
assert sha(d/'sink-program.hex')==sha(BASE/'probes/nes-repeat227/asm02/sink-program.hex')==rom['expected_hex_sha256']
programmer=json.loads((BASE/'probes/nes-nrom423/programmer01/result.json').read_text())
visual=json.loads((BASE/'probes/nes-nrom424/mesen11/result.json').read_text())
loader=json.loads((BASE/'probes/nes-nrom424/loader01/result.json').read_text())
fixture=BASE/'probes/nes-nrom424/fixture02/nrom16.nes'
assert programmer['passed'] and programmer['image_sha256']==sha(d/'fpga_nrom16.bi3') and programmer['rbf_sha256']==sha(d/'board.rbf')
assert visual['passed'] and loader['passed'] and visual['rom_sha256']==loader['fixture_rom_sha256']==sha(fixture)
result={'firmware_stm':sha(arm),'fpga_bi3':sha(d/'fpga_nrom16.bi3'),'rbf':sha(d/'board.rbf'),
 'sof':sha(d/'board.sof'),'rle_roundtrip':True,'encoded_bytes':len(enc),'rbf_bytes':len(rbf),
 'snes_program_hex':sha(d/'sink-program.hex'),'snes_postfit_default_netlists':1,
 'snes_postfit_check':sha(BASE/'probes/nes-nrom423/nrom423-romcheck02/result.json'),
 'timing_status':'raw STA negative and incompletely constrained; hardware package not approved',
 'visual_fixture_sha256':sha(fixture),'visual_fixture_mesen_injected_input':True,
 'actual_controller_test':False,'base_recovery_actual':False,'physical_test':False}
(ROOT/'analysis/nrom423-pair.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
