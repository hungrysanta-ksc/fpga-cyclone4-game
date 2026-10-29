# SPDX-License-Identifier: MIT
"""Read-only audit of preserved NES227 artifacts and hardware evidence.

Does not extract or publish game ROM bytes, change firmware, or run hardware.
"""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from nes_delta231 import BASE, ROOT


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    release = json.loads((ROOT / 'analysis/release227-verification.json').read_text(encoding='utf-8'))
    hardware = json.loads((ROOT / 'analysis/game227-hardware01-verification.json').read_text(encoding='utf-8'))
    bundle = BASE / 'probes/nes-repeat227/release01/NES227-SMB3-OAMREPEAT.zip'
    assert sha(bundle) == release['zip_sha256']
    expected = {
        '01-GAME227-SD-ROOT/sd2snes/firmware.stm': release['firmware_sha256'],
        '01-GAME227-SD-ROOT/sd2snes/fpga_n227.bi3': release['fpga_sha256'],
        '02-RESTORE164-SD-ROOT/sd2snes/firmware.stm': release['preserved']['02-RESTORE164-SD-ROOT/sd2snes/firmware.stm'],
        '02-RESTORE164-SD-ROOT/sd2snes/fpga_n164.bi3': release['preserved']['02-RESTORE164-SD-ROOT/sd2snes/fpga_n164.bi3'],
        '01-GAME227-SD-ROOT/sd2snes/fpga_base.bi3': release['preserved']['01-GAME227-SD-ROOT/sd2snes/fpga_base.bi3'],
    }
    with zipfile.ZipFile(bundle) as z:
        files = {name: {'size': z.getinfo(name).file_size, 'sha256': sha_bytes(z.read(name))} for name in expected}
    assert all(files[name]['sha256'] == value for name, value in expected.items())
    built = {
        'FPGA': BASE / 'probes/nes-repeat227/asm02/fpga_n227.bi3',
        'ARM': BASE / 'probes/nes-repeat227/arm01/src/obj-nes-100/firmware.stm',
    }
    assert sha(built['FPGA']) == release['fpga_sha256']
    assert sha(built['ARM']) == release['firmware_sha256']
    fit = BASE / 'probes/nes-repeat227/asm02/output_files/board.fit.summary'
    fit_ref = BASE / 'probes/nes-counter224/mapfit02/output_files/board.fit.summary'
    assert fit.read_bytes() == fit_ref.read_bytes()
    fit_text = fit.read_text(errors='replace')
    assert 'Fitter Status : Successful' in fit_text and 'EP4CE15F17C8' in fit_text
    loader = BASE / 'probes/nes-repeat227/arm01/src/nes_h1_stm32.c'
    text = loader.read_text(encoding='utf-8')
    assert all(s in text for s in ('header[4]!=16', 'header[5]!=16', 'header[6]!=0x42', 'total=0x60000u'))
    cart = BASE / 'probes/nes-repeat227/asm02/cart_nrom.sv'
    assert re.search(r'MMC3\s+mapper\s*\([^;]*\.flags\(32\x27d4\)', cart.read_text(), re.S)
    logs = BASE / 'probes/nes-game227-hardware01/raw'
    log_files = {}
    for name in ('nes-progress-227.txt', 'nes-budget-227.txt', 'nes-game-last-227.txt'):
        path = logs / name
        assert sha(path) == hardware['raw_inputs'][name]['sha256']
        log_files[name] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    result = {
        'passed': True, 'scope': 'read-only historical provenance audit; no NROM test or new FIT/STA',
        'package_sha256': sha(bundle), 'package_bytes': bundle.stat().st_size, 'package_files': files,
        'build_matches_package': {name: sha(path) for name, path in built.items()},
        'old_224_fit_summary_sha256': sha(fit), 'old_fit_is_identical_224': True,
        'old_fit_tool': 'historical Standard; no new Standard run',
        'old_fit_LE': 15249, 'device_LE': 15408,
        'production_loader_source_sha256': sha(loader), 'production_cart_source_sha256': sha(cart),
        'production_loader_header': 'SMB3 mapper4 PRG256KiB CHR128KiB; exact length and CRC',
        'cart_mapper': 'MMC3 flags 4', 'production_NROM_supported': False,
        'hardware_log_hashes': log_files,
        'hardware_227': {'display_ack_count': 465, 'duration_seconds': 60.06,
                         'user_reported_screen_audio_input_menu': True,
                         'whole_run_ack_per_second': 465 / 60.06,
                         'scroll_fps_measured': False, 'physical_60fps_proven': False},
        'new_hardware_test': False, 'new_FPGA_build': False,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'passed': True, 'package_sha256': result['package_sha256'], 'production_NROM_supported': False,
                      'old_fit_LE': result['old_fit_LE'], 'new_hardware_test': False}, indent=2))


if __name__ == '__main__':
    main()
