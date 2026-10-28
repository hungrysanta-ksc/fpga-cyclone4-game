# SPDX-License-Identifier: MIT
"""Audit exact-source NROM cart diagnostic, unit tests and whole Lite MAP."""
import json
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha

base=BASE/'probes/nes-nrom406'
a=json.loads((base/'map-base01/result.json').read_text())
b=json.loads((base/'map-cart01/result.json').read_text())
unit=json.loads((base/'layout02/result.json').read_text())
assert a['passed'] and b['passed'] and unit['passed']
assert set(a['inputs'])==set(b['inputs'])
changed=[k for k in a['inputs'] if a['inputs'][k]!=b['inputs'][k]]
assert changed==['cart_nrom.sv'] and len(a['inputs'])==90
assert b['cart_sha256']==sha(base/'cart02/cart_nrom.sv')
assert 'NROM406 CART PASS' in (base/'cart02/simulation.log').read_text(errors='replace')
assert 'Errors: 0, Warnings: 0' in (base/'cart02/simulation.log').read_text(errors='replace')
assert unit['source']==sha(ROOT/'src/nes/firmware/nes_nrom406.c')
assert unit['header']==sha(ROOT/'src/nes/firmware/nes_nrom406.h')
assert unit['verify_test']==sha(ROOT/'tests/nes-nrom406/verify_test.c')
result={'passed':True, 'scope':'fixed NROM16 horizontal cart_top on 227 board MAP; no NROM loader integration or timing',
        'input_count':90, 'changed_inputs':changed,
        'reference_cart':a['cart_sha256'],'candidate_cart':b['cart_sha256'],
        'cart_testbench':sha(ROOT/'tests/nes-nrom406/cart_tb.sv'),
        'cart_simulation':sha(base/'cart02/simulation.log'),
        'layout_unit':unit,
        'whole_reference':{'LE':18850,'comb':13951,'FF':8353,'RAM_bits':256608},
        'whole_candidate':{'LE':18178,'comb':13557,'FF':8029,'RAM_bits':185824},
        'whole_delta':{'LE':-672,'comb':-394,'FF':-324,'RAM_bits':-70784},
        'RAM_delta_explanation':{'PRG_RAM_pruned_bits':65536,'compact_capture_reduction_bits':5248,
                                 'PRG_RAM_supported_by_candidate':False},
        'full_loader_STOP_recovery':False,'whole_functional_board_run':False,
        'ARM_IRQ_SPI_time_ms':None,'MMC4_MMC5_new_time_ms':None,
        'FIT':False,'STA':False,'physical60fps':False}
for key in ('18,850','13,951','8,353','256,608'):
 assert key in a['summary'],key
for key in ('18,178','13,557','8,029','185,824'):
 assert key in b['summary'],key
out=ROOT/'analysis/nrom406-verification.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:result[k] for k in ('passed','changed_inputs','whole_delta','full_loader_STOP_recovery','FIT')},indent=2))
