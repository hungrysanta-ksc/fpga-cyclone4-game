# SPDX-License-Identifier: MIT
"""Bind strict loader, linked firmware and whole-board479 evidence; no game approval."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def resources(path):
    s = path.read_text()
    def value(label):
        return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)', s)[1].replace(',', ''))
    return {k: value(v) for k, v in [('LE', 'Total logic elements'), ('comb', 'Total combinational functions'), ('FF', 'Dedicated logic registers'), ('RAM_bits', 'Total memory bits')]}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['candidate', 'arm', 'loader', 'board', 'core', 'm4', 'objects', 'out']:
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args()
    prep = json.loads((a.candidate/'preparation.json').read_text())
    host = json.loads((a.loader/'result.json').read_text())
    assert host['passed'] and host['cases'] == 20 and host['full_payload_compared'] == 0x60000
    for n, h in prep['ARM_patch'].items():
        assert sha(a.arm/'src'/n) == sha(a.candidate/'arm'/n) == h, n
    for n, h in prep['native476_unchanged'].items():
        assert sha(a.arm/'src'/n) == h, n
    for field, n in [('loader_sha256', 'nes_h1_stm32.c'), ('run136_sha256', 'nes_run136.inc'), ('verify_sha256', 'nes_rom_verify.c')]:
        assert host[field] == sha(a.arm/'src'/n), n
    board_pins = dict(prep['board_base'])
    board_pins.update(prep['board_changed'])
    for n, h in board_pins.items():
        assert sha(a.board/n) == h, n
    for kind in ['map', 'fit']:
        assert 'Successful' in (a.board/f'output_files/board.{kind}.summary').read_text()
    fit = resources(a.board/'output_files/board.fit.summary')
    ref = json.loads((ROOT/'analysis/game478-feasibility.json').read_text())['MMC3']['FIT_candidate']
    size = (a.arm/'size.log').read_text()
    match = re.search(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+[0-9a-f]+\s+.*sd2snes.elf', size, re.M)
    assert match
    binary = a.arm/'src/obj-nes-100/firmware.stm'
    timing = {}
    for view in ['implementation', 'nominal']:
        rows = list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(), delimiter='\t'))
        timing[view] = {k: min(float(x['slack']) for x in rows if x['kind'] == k and ((x['from_clock']=='nes') == (x['to_clock']=='nes'))) for k in ['setup', 'hold']}
    sta = (a.board/'output_files/board.sta.summary').read_text()
    raw = {k: min(map(float, re.findall(r'Type\s*:[^\n]*\b'+k+r'\b[^\n]*\nSlack\s*:\s*(-?[\d.]+)', sta))) for k in ['Setup', 'Recovery']}
    core_log = a.core/'simulation.log'
    core_result = a.core/'result.json'
    core = json.loads(core_result.read_text()) if core_result.exists() else {'passed': False, 'status': 'no passing result; inspect preserved raw log'}
    if core.get('passed'):
        assert core['cart_sha256'] == sha(a.board/'cart_nrom.sv')
        assert core['fixture_sha256'] == host['original_ROM_sha256']
        for n, h in board_pins.items():
            assert sha(a.core/n) == h, ('simulation source mismatch', n)
    m4 = json.loads((a.m4/'result.json').read_text())
    assert m4['passed'] and m4['candidate479']['firmware_SHA256'] == sha(binary)
    assert m4['actual_RTL_blocks_SHA256'] == core['blocks_sha256']
    objects = json.loads(a.objects.read_text())
    assert objects['unchanged_ALLOC_object_count'] == 73
    result = {
        'scope': __doc__, 'stage1_loader_build_fit_passed': True,
        'profile_hex': '79', 'NROM78_and_legacy74_rejected': True,
        'strict_ROM': {'SHA256': host['original_ROM_sha256'], 'CRC32': '5a04eed7', 'file_bytes': 0x60010, 'PRG': 0x40000, 'CHR': 0x20000, 'three_CRC_passes_and_full_readback': True},
        'ARM_patch': prep['ARM_patch'], 'native476_unchanged': prep['native476_unchanged'],
        'ARM': {'text': int(match[1]), 'data': int(match[2]), 'BSS': int(match[3]), 'firmware_bytes': binary.stat().st_size, 'firmware_SHA256': sha(binary), 'firmware_delta_vs476': binary.stat().st_size-212640, 'physical_Flash_tail': 262144-49152-binary.stat().st_size, 'loader_stack_report': (a.arm/'src/obj-nes-100/nes_h1_stm32.su').read_text(), 'full_stack_or_timing_proof': False},
        'loader_host': host, 'whole_board_inputs': board_pins,
        'MAP': resources(a.board/'output_files/board.map.summary'), 'FIT': fit, 'FIT_delta_vs478': {k: fit[k]-ref[k] for k in fit}, 'remaining_LE': 15408-fit['LE'],
        'related_timing_ns': timing, 'raw_STA_min_ns': raw, 'full_CDC_IO_signoff': False,
        'core_smoke': core, 'core_log_SHA256': sha(core_log) if core_log.exists() else None,
        'actual_RTL_to_M4_replay': m4, 'unchanged_object_sections': objects,
        'actual_ARM_IRQ_SPI_ROM_timing': None, 'actual_game_FPS': None,
        'game_hardware_approved': False, 'game_installer_created': False,
        'failures_preserved': ['ARM01 sandbox subst denied; ARM02 fresh old-make implicit rule search failed before generated headers; debug retry passed; ARM03 explicit header bootstrap passed', 'loader01 sandbox MinGW WinError623 before test execution; loader02 same test outside sandbox passed'],
        'next': ['actual live ARM/tile plan/query/ROM and staging concurrency; MMC3 bank/IRQ coverage', 'paired65816 DMA/independent check/finalACK/EA and STOP/base/menu before game installer', 'measure actual same-game cadence; no prediction from NROM24fps'],
        'scripts': {n: sha(ROOT/'tools'/n) for n in ['prepare_nes_mmc479.py', 'build_nes_mmc479_arm.ps1', 'test_nes_mmc479_loader.py', 'test_nes_mmc479_core.py', 'check_nes_mmc479_arm.py', 'analyze_nes_mmc479.py']},
        'raw': 'probes/nes-mmc479; ARM03/loader02/core01/board01 execution folders in local Temp; no ROM in Git',
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8', newline='\n')
    print(json.dumps({'stage1': True, 'loader_cases': 20, 'FIT_LE': fit['LE'], 'core_smoke': core.get('passed'), 'hardware': False}))
