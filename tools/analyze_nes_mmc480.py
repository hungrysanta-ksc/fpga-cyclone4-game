# SPDX-License-Identifier: MIT
"""Bind480 live functional/pixel gates to exact479 RTL and newly labeled480 ARM."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf8'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['live', 'arm', 'assembly', 'm4', 'pixels', 'out']:
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args()
    old = read(ROOT/'analysis/mmc479-verification.json')
    live = read(a.live/'result.json')
    pixels = read(a.pixels)
    assembly = read(a.assembly/'result.json')
    m4 = read(a.m4/'result.json')
    assert all(x['passed'] for x in [live, pixels, assembly, m4])
    assert pixels['pixels'] == 57344 and pixels['mismatches'] == 0
    assert pixels['screen_SHA256'] == live['frame_sha256']
    assert pixels['source_SHA256'] == live['golden_NES_colors_SHA256']
    assert live['consumer']['commits'] == 1 and live['consumer']['acks'] == 34 and live['consumer']['retired_chunks'] == 2
    fw = a.arm/'src/obj-nes-100/firmware.stm'
    assert sha(fw) == m4['candidate479']['firmware_SHA256']
    assert sha(a.assembly/'fpga_mmc480.bi3') == assembly['BI3_SHA256']
    for n, h in old['whole_board_inputs'].items():
        assert sha(a.live/n) == h, n
    for n, h in old['native476_unchanged'].items():
        assert sha(a.live/n) == sha(a.arm/'src'/n) == h, n
    assert sha(a.live/'nes_rom_verify.c') == old['loader_host']['verify_sha256']
    # Prove that the480 delivery build changed only menu/checkpoint constants.
    sys.path.insert(0, str(ROOT.parent/'.tools/arm259-python'))
    from elftools.elf.elffile import ELFFile
    baseline = ROOT.parent/'probes/nes-mmc479/executed/ARM03/src/obj-nes-100'
    def allocated(path):
        with path.open('rb') as f:
            return {s.name: sha_bytes(s.data()) for s in ELFFile(f).iter_sections() if s['sh_flags']&2}
    def sha_bytes(data):
        return hashlib.sha256(data).hexdigest()
    same, changed = [], []
    obj = a.arm/'src/obj-nes-100'
    for f in obj.rglob('*.o'):
        relative = f.relative_to(obj)
        (same if allocated(f) == allocated(baseline/relative) else changed).append(str(relative))
    assert len(same) == 75 and set(changed) == {'nes_checkpoint112.o', 'nes_menu_diagnostic.o'}
    # Map the exact4KiB boot-ROM image into the32KiB Mesen client image.
    client = ROOT.parent/'probes/nes-repeat227/snes04/client/sink165.sfc'
    prg = bytes.fromhex((a.live/'sink-program.hex').read_text())
    binary = client.read_bytes()
    assert len(prg)==4096 and prg[:4032]==binary[:4032] and prg[4032:]==binary[-64:]
    assert sha(client) == live['client_sha256']
    observations = []
    for f in sorted(a.live.glob('H-*.req')):
        wire = f.read_bytes()
        if wire[0] == 1 and len(wire) >= 16 and wire[8] == 0x70:
            rx = f.with_suffix('.rsp').read_bytes()
            assert len(rx) == 8 and rx[1] == 0xe5 and rx[3] == 0
            observations.append({'flags': rx[2], 'ROM_error': rx[3], 'count': int.from_bytes(rx[4:8], 'big')})
    assert len(observations) >= 2 and observations[-1]['flags'] == 1
    assert observations[-1]['count'] == observations[-2]['count']
    result = {
        'passed': True, 'candidate': 'MMC480 limited SMB3 trial', 'profile_hex': '79',
        'limited_trial_ready': True, 'hardware_verified': False, 'physical_FPS': None,
        'scope': __doc__, 'live_functional': live, 'independent_PPU_pixels': pixels,
        'actual_source_M4_replay': m4, 'retained_observer': observations, 'ARM_label_only_object_change': {'same_count': len(same), 'changed': changed},
        'ARM': {'firmware_SHA256': sha(fw), 'firmware_bytes': fw.stat().st_size, 'text': 202313, 'data': 10040, 'BSS': 18552, 'physical_Flash_tail': 636, 'same_RUN_workspace_bytes': 31848, 'full_stack_proof': False},
        'FPGA': assembly, 'FIT': old['FIT'], 'remaining_LE': old['remaining_LE'],
        'related_timing_ns': old['related_timing_ns'], 'raw_STA_min_ns': old['raw_STA_min_ns'], 'full_CDC_IO_signoff': False,
        'physical_baseline': {'candidate': 'NROM476', 'fps': 23.838854669552187, 'same_game_comparison': False},
        'limits': ['One opening-curtain game capture; not world map/1-1/whole-game or sustained60fps proof', 'actual selected ARM C at host ABI, synthetic ticks/service and transaction RPC; no M4/IRQ cycle timeline', 'PSRAM70ns and verified loader are seeded; no full384KiB live loader repetition', 'CPU/PPU/MMC3 ROM competition occurs during transaction simulation; no continuous full ARM/IRQ/ROM hardware bound', 'GPIO console setup/reset/base menu recovery are prior unchanged code plus479 host20-case gates, not physical480 proof', 'audio and broad MMC3 banking/IRQ/other mappers remain unverified'],
        'preserved_failures': ['float01/02 Python adapter syntax errors, before RTL run; fixed/prepare-only checked before float03', 'pixels01 compared SNES239 buffer at row0; primary Mesen PPU contract specifies7 top/8 bottom black rows; pixels02 all57344 visible pixels exact, borders checked; no RTL/ARM color/coordinate change'],
        'raw': 'probes/nes-mmc480, live01 and ARM01 execution folders; private ROM/PPU/RGB/trace not in Git',
        'scripts': {n: sha(ROOT/'tools'/n) for n in ['test_nes_mmc480_live.py', 'check_nes_mmc480_pixels.py', 'prepare_nes_mmc480_delivery.py', 'assemble_nes_mmc480.py', 'analyze_nes_mmc480.py']},
    }
    a.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8', newline='\n')
    print(json.dumps({'passed': True, 'limited_trial_ready': True, 'pixels_exact': 57344, 'ACKs': 34, 'hardware': False}))
