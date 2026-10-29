# SPDX-License-Identifier: MIT
"""Replay recorded source SPI through linked M4 poll/prepare, counting instructions."""
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent / '.tools/arm259-python'))
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_XPSR)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile(arm, rpc, fault=None):
    firmware = arm / 'obj-nes-100/firmware.stm'
    elf = arm / 'obj-nes-100/sd2snes.elf'
    flash = firmware.read_bytes()
    events = []
    for request in sorted(rpc.glob('H-*.req')):
        wire = request.read_bytes()
        if wire[:1] != b'\x01' or wire[8] not in (0xd0, 0xd1, 0xd2, 0xd3):
            continue
        response = request.with_suffix('.rsp')
        events.append((wire[8:], response.read_bytes(), request.name))
    assert events
    functions, lines, members = [], [], {}
    with elf.open('rb') as stream:
        image = ELFFile(stream)
        segments = [(s['p_vaddr'], s['p_paddr'], s.data()) for s in image.iter_segments()
                    if s['p_type'] == 'PT_LOAD' and s['p_filesz']]
        for address, physical, data in segments:
            assert flash[physical-0x0800c000:physical-0x0800c000+len(data)] == data
        for s in image.get_section_by_name('.symtab').iter_symbols():
            if s['st_info']['type'] == 'STT_FUNC' and s['st_size']:
                functions.append((s['st_value'] & ~1, s['st_size'], s.name))
        dwarf = image.get_dwarf_info()
        for cu in dwarf.iter_CUs():
            table = dwarf.line_program_for_CU(cu)
            if table:
                files = table['file_entry']
                for entry in table.get_entries():
                    state = entry.state
                    if state:
                        name = files[state.file-1].name.decode() if not state.end_sequence else ''
                        lines.append((state.address, name.rsplit('/', 1)[-1], state.line or 0))
            for die in cu.iter_DIEs():
                if (die.tag == 'DW_TAG_structure_type' and die.attributes.get('DW_AT_name')
                        and die.attributes['DW_AT_name'].value == b'nes_native165'
                        and die.attributes.get('DW_AT_byte_size')):
                    layout = {'size': die.attributes['DW_AT_byte_size'].value}
                    for child in die.iter_children():
                        if child.tag != 'DW_TAG_member' or not child.attributes.get('DW_AT_name'):
                            continue
                        offset = child.attributes['DW_AT_data_member_location'].value
                        if not isinstance(offset, int):
                            assert offset[0] == 0x23
                            value, shift = 0, 0
                            for byte in offset[1:]:
                                value |= (byte & 127) << shift
                                if byte < 128:
                                    break
                                shift += 7
                            offset = value
                        layout[child.attributes['DW_AT_name'].value.decode()] = offset
                    assert not members or members == layout
                    members = layout
    functions.sort()
    lines.sort(key=lambda row: row[0])
    starts, line_starts = [x[0] for x in functions], [x[0] for x in lines]
    symbols = {name: start for start, size, name in functions}
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    uc.mem_map(0x08000000, 0x80000)
    uc.mem_map(0x20000000, 0x20000)  # isolated unit storage, NOT physical RUN stack proof
    for address, physical, data in segments:
        uc.mem_write(address, data)
    state, end, callback = 0x20008000, 0x0807fff0, 0x0807ffe0
    counts, source_counts, pc_counts = Counter(), Counter(), Counter()
    cursor, total, packet_count, injected = 0, 0, 0, 0
    boundaries = []

    def check_crc(data, width, polynomial, initial):
        result = initial
        for byte in data:
            result ^= byte << (width-8)
            for _ in range(8):
                result = ((result << 1) ^ (polynomial if result & (1 << (width-1)) else 0)) & ((1 << width)-1)
        return result

    def hook(cpu, address, size, user):
        nonlocal cursor, total, packet_count, injected
        if address == end:
            cpu.emu_stop()
            return
        if address == callback:
            assert cursor < len(events), ('extra transfer', cursor)
            tx, rx, name = events[cursor]
            length = cpu.reg_read(UC_ARM_REG_R3)
            actual = bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1), length))
            assert actual == tx and len(rx) == length, (name, actual.hex(), tx.hex())
            rx = bytearray(rx)
            transfer_ok = True
            if not injected:
                if fault == 'status_crc' and tx[0] == 0xd0:
                    rx[-1] ^= 1; injected = 1
                elif tx[0] == 0xd1:
                    if fault == 'read_crc':
                        rx[-1] ^= 1; injected = 1
                    elif fault == 'read_payload':
                        rx[5] ^= 1; injected = 1
                    elif fault == 'read_transfer':
                        transfer_ok = False; injected = 1
                    elif fault == 'geometry_with_valid_crc':
                        rx[5] ^= 1
                        rx[-2:] = check_crc(rx[1:-2], 16, 0x1021, 65535).to_bytes(2, 'big')
                        injected = 1
                elif fault == 'pop_crc' and tx[0] == 0xd2:
                    rx[-1] ^= 1; injected = 1
                elif (fault == 'retire_token' and tx[0] == 0xd0 and cursor
                      and events[cursor-1][0][0] == 0xd2):
                    rx[4] ^= 1
                    rx[-1] = check_crc(rx[1:-1], 8, 7, 0)
                    injected = 1
                elif fault == 'prepare_transfer' and tx[0] == 0xd3:
                    transfer_ok = False; injected = 1
            cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2), bytes(rx))
            if tx[0] == 0xd1:
                packet_count += 1
                boundaries.append({'packet': packet_count, 'bytes': len(tx)-3, 'instructions_before_read': total})
            cursor += 1
            cpu.reg_write(UC_ARM_REG_R0, int(transfer_ok))
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
            return
        total += 1
        pc_counts[address] += 1
        at = bisect_right(starts, address)-1
        if at >= 0:
            start, width, name = functions[at]
            counts[name if address < start+width else '<gap>'] += 1
        at = bisect_right(line_starts, address)-1
        if at >= 0:
            start, name, line = lines[at]
            source_counts[f'{name}:{line}' if name else '<no-line>'] += 1

    uc.hook_add(UC_HOOK_CODE, hook)

    def call(name, args):
        for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
            uc.reg_write(register, value)
        uc.reg_write(UC_ARM_REG_SP, 0x2001f000)
        uc.reg_write(UC_ARM_REG_LR, end | 1)
        uc.reg_write(UC_ARM_REG_XPSR, 0x01000000)
        uc.emu_start(symbols[name] | 1, end+2, count=20000000)
        assert uc.reg_read(UC_ARM_REG_PC) == end, name
        return uc.reg_read(UC_ARM_REG_R0)

    call('nes_native165_reset', [state])
    initial = total
    while cursor < len(events):
        before = cursor
        status = uc.mem_read(state+members['state'], 1)[0]
        if status == 2:
            success = call('nes_native165_prepare', [state, 1, callback | 1, 0])
        else:
            success = call('nes_native165_poll', [state, callback | 1, 0])
        if not success:
            assert fault and injected
            break
        assert cursor > before
    expected_errors = {'status_crc':21, 'read_crc':23, 'read_payload':23,
        'read_transfer':23, 'geometry_with_valid_crc':2, 'pop_crc':24,
        'retire_token':27, 'prepare_transfer':26}
    if fault:
        assert injected and uc.mem_read(state+members['state'], 1)[0] == 5
        assert uc.mem_read(state+members['error'], 1)[0] == expected_errors[fault]
        frozen = bytes(uc.mem_read(state, members['size']))
        before = cursor
        assert call('nes_native165_poll', [state, callback | 1, 0]) == 0
        assert call('nes_native165_prepare', [state, 1, callback | 1, 0]) == 0
        call('nes_native165_consumed', [state])
        assert cursor == before and bytes(uc.mem_read(state, members['size'])) == frozen
    else:
        assert uc.mem_read(state+members['state'], 1)[0] == 4
    canonical = bytes(uc.mem_read(state, members['token_valid']))
    return {'firmware_sha256': sha(firmware), 'elf_sha256': sha(elf),
            'fault':fault, 'failed_state_frozen_without_more_SPI':bool(fault),
            'full_state_sha256':hashlib.sha256(bytes(uc.mem_read(state,members['size']))).hexdigest(),
            'source_transactions':cursor, 'source_read_packets': packet_count,
            'canonical_prefix_sha256': hashlib.sha256(canonical).hexdigest(),
            'canonical_prefix_bytes': len(canonical), 'reset_instructions': initial,
            'instructions': total, 'functions': counts.most_common(),
            'source_lines': source_counts.most_common(), 'packet_boundaries': boundaries,
            'source_inputs': {p.name: sha(p) for p in sorted(rpc.glob('H-*'))
                              if any(p.stem == name[:-4] for tx, rx, name in events)},
            'scope': 'Actual linked M4 poll/prepare with exact recorded SPI replies and TX equality; instruction counts only. SPI time, IRQ, complete ARM RUN, physical stack, NES/SNES timing and FPS are not measured.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', type=Path, required=True)
    parser.add_argument('--rpc', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    result = profile(args.arm, args.rpc)
    (args.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['instructions', 'source_read_packets', 'canonical_prefix_sha256', 'functions']}))
