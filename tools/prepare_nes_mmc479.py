# SPDX-License-Identifier: MIT
"""Strict SMB3(J) loader + distinct MMC3 identity on selected476/478 sources.

Private materialization only; this does not approve a hardware package.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'nes_h1_stm32.c': 'f3a425b1f8d0a666ddb8d7aa0b8b5973ade390a84f31b2a547917a413cc5d6b9',
    'nes_rom_verify.c': '4be439ac6e3f3fc2661f8c63230809924a35db1e9684b5f96563e0052f926875',
    'nes_run136.inc': '84058b0f0c14c9c908d988cef04808e645a2c247cb905f2b6983c407b27800a1',
    'nes_menu_diagnostic.c': 'e2db2d9813b5968f1702c15830c647e60d4d3a5f828baaecc8127e6852c59163',
    'nes_checkpoint112.c': '82fc549c9fc51cdf98909597d5b45e7f8dde2f89a6f6147ac886376fe3d544aa',
    'Makefile': 'c2b511ffe6ee1a47f5e91c4b4ad26fbcb28060e79fe046aa18eb7ec0acc57aed',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def replace(s, old, new, count=1):
    assert s.count(old) == count, (old, s.count(old))
    return s.replace(old, new)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['arm', 'reference', 'board', 'out']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    for n, digest in PINS.items():
        assert sha(a.arm / n) == digest, n
    selected = json.loads((ROOT / 'analysis/receive476-verification.json').read_text())
    for n, digest in selected['ARM_changed_inputs'].items():
        assert sha(a.arm / n) == digest, n
    assert sha(a.reference) == 'e5e41ce4975c15c278dbbdc1f290338b59327e0b5d42cc12fb4738cac9bcfffb'
    board_pins = json.loads((ROOT / 'analysis/game478-feasibility.json').read_text())['MMC3']
    inputs = dict(board_pins['base_QSF_inputs'])
    inputs.update(board_pins['restored_cart'])
    inputs.update(board_pins['auto_found_dependencies_now_pinned'])
    inputs.update(board_pins['transitive_SDC_now_pinned'])
    inputs['board.qsf'] = board_pins['QSF_sha256']
    for n, digest in inputs.items():
        assert sha(a.board / n) == digest, n
    a.out.mkdir(parents=True, exist_ok=False)
    patch = a.out / 'arm'
    patch.mkdir()
    for n in PINS:
        shutil.copyfile(a.arm / n, patch / n)
    # Restore the original STRICT 227 SMB3 loader, not a permissive NROM loader.
    # Its framing, three CRC passes, complete physical readback, STOP/base cleanup
    # remain intact. Current native476 includes stay in the full ARM source tree.
    s = a.reference.read_text()
    s = replace(s, '#include "nes_native165_bulk.inc"', '#include "nes_native165_bulk.inc"\n#include "nes_mmc479.h"')
    s = replace(s, 'rx[1]!=0x74||(rx[4]&0xf8)', 'rx[1]!=NES_MMC479_BOARD_ID||(rx[4]&0xf8)')
    s = replace(s, 'expected_crc=0x5a04eed7u;', 'expected_crc=NES_MMC479_ROM_CRC;')
    (patch / 'nes_h1_stm32.c').write_text(s, newline='\n')
    header = '''/* SPDX-License-Identifier: MIT */
#ifndef NES_MMC479_H
#define NES_MMC479_H
/* Fixed SMB3(J), mapper4, PRG256KiB/CHR128KiB, original 16B iNES header.
 * Distinct from NROM78 and historical MMC3/74. CRC is accidental-error detection.
 */
#define NES_MMC479_BOARD_ID 0x79
#define NES_MMC479_ROM_CRC 0x5a04eed7u
#endif
'''
    (patch / 'nes_mmc479.h').write_text(header, newline='\n')
    for n, count in [('nes_rom_verify.c', 2), ('nes_run136.inc', 1)]:
        s = (patch / n).read_text()
        s = replace(s, '0x78', 'NES_MMC479_BOARD_ID', count)
        (patch / n).write_text('#include "nes_mmc479.h"\n' + s, newline='\n')
    n = patch / 'Makefile'
    n.write_text(replace(n.read_text(), 'nes_cost471.c nes_nrom406.c', 'nes_cost471.c'), newline='\n')
    for n in ['nes_menu_diagnostic.c', 'nes_checkpoint112.c']:
        s = (patch / n).read_text()
        s = s.replace('nrom476', 'mmc479').replace('NROM476', 'MMC479')
        s = s.replace('NES NROM 476.nh1', 'NES MMC3 479.nh1')
        s = replace(s, 'board_expected_hex=78', 'board_expected_hex=79') if n.startswith('nes_menu') else s
        (patch / n).write_text(s, newline='\n')
    board = a.out / 'board'
    board.mkdir()
    for n in [*inputs, 'board.qpf']:
        target = board / n
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a.board / n, target)
    n = board / 'nes_rom_spi.sv'
    n.write_text(replace(n.read_text(), "8'h78,flags", "8'h79,flags", 2), newline='\n')
    result = {
        'scope': __doc__, 'ARM476_base': PINS, 'native476_unchanged': selected['ARM_changed_inputs'],
        'strict227_loader': sha(a.reference), 'ARM_patch': {n.name: sha(n) for n in patch.iterdir()},
        'board_base': inputs, 'board_changed': {'nes_rom_spi.sv': sha(n)},
        'profile_hex': '79', 'ROM_CRC_hex': '5a04eed7', 'ROM_file_bytes': 0x60010,
        'PRG_bytes': 0x40000, 'CHR_bytes': 0x20000, 'direct_payload_layout': True,
        'logs': [f'nes-{k}-mmc479.txt' for k in ['progress', 'game-last', 'budget']],
        'hardware_approved': False, 'game_functionality_tested': False,
    }
    (a.out / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'profile': '79', 'ARM_patch_files': len(result['ARM_patch']), 'hardware_approved': False}))


if __name__ == '__main__':
    main()
