# SPDX-License-Identifier: MIT
"""Compile one M4 restoration kernel; execute exact captures and atomic rejects.

Instruction counts are not MCU cycles, IRQ service, full firmware or Flash net gain.
"""
import argparse
import json
import struct
import subprocess
from pathlib import Path
from check_nes_game478 import (ELFFile, Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS,
    UC_HOOK_CODE, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_XPSR, encode, sha)
from nes_row583 import encode_rows, restore_rows, row_block
from nes_abi582 import ROOT, canonical


class Kernel:
    def __init__(self, elf):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.u.mem_map(0x08000000, 65536)
        self.u.mem_map(0x20000000, 131072)
        self.end = 0x0800fff0
        with elf.open('rb') as f:
            e = ELFFile(f)
            for s in e.iter_segments():
                if s['p_type'] == 'PT_LOAD' and s['p_filesz']:
                    self.u.mem_write(s['p_vaddr'], s.data())
            self.entry = e.get_section_by_name('.symtab').get_symbol_by_name('nes_row583_apply')[0]['st_value']
            self.text = e.get_section_by_name('.text')['sh_size']
            self.alloc = {s.name: s['sh_size'] for s in e.iter_sections() if s['sh_flags'] & 2}
        self.u.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, u, addr, size, ctx):
        if addr == self.end:
            u.emu_stop(); return
        self.instructions += 1
        self.low_sp = min(self.low_sp, u.reg_read(UC_ARM_REG_SP))

    def call(self, old, b, count, have):
        map_addr, packet, stack = 0x20000010, 0x20002000, 0x2001e000
        memory = struct.pack('<1056H', *(old + [0x55aa] * (1056 - len(old))))
        self.u.mem_write(map_addr - 16, bytes([0x69]) * 16 + memory + bytes([0x96]) * 16)
        self.u.mem_write(packet, b)
        for r, v in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3),
                         (map_addr, count, packet, len(b))):
            self.u.reg_write(r, v)
        self.u.mem_write(stack, struct.pack('<I', have))
        self.u.reg_write(UC_ARM_REG_SP, stack)
        self.u.reg_write(UC_ARM_REG_LR, self.end | 1)
        self.u.reg_write(UC_ARM_REG_XPSR, 0x01000000)
        self.instructions = 0; self.low_sp = stack
        self.u.emu_start(self.entry | 1, self.end + 2, count=100000)
        assert self.u.reg_read(UC_ARM_REG_PC) == self.end
        assert bytes(self.u.mem_read(map_addr - 16, 16)) == bytes([0x69]) * 16
        assert bytes(self.u.mem_read(map_addr + 2112, 16)) == bytes([0x96]) * 16
        result = list(struct.unpack('<1056H', self.u.mem_read(map_addr, 2112)))
        return self.u.reg_read(UC_ARM_REG_R0), result, self.instructions, stack - self.low_sp


def run(a):
    a.out.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'tools/nes_row583.c'
    elf = a.out / 'row583.elf'
    cmd = [str(a.cc), '-mcpu=cortex-m4', '-mthumb', '-Os', '-std=c99', '-ffreestanding',
           '-fno-builtin', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
           '-fstack-usage', '-nostdlib', '-Wl,-Ttext=0x08000000,-e,nes_row583_apply,--build-id=none',
           str(source), '-o', str(elf)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    (a.out / 'build.log').write_text(p.stdout + p.stderr, encoding='utf8')
    assert p.returncode == 0, p.stderr
    (a.out / 'command.json').write_text(json.dumps(cmd, indent=2) + '\n')
    version = subprocess.check_output([str(a.cc), '--version'], text=True)
    (a.out / 'compiler.txt').write_text(version)
    objdump = a.cc.with_name('arm-none-eabi-objdump.exe')
    disassembly = subprocess.check_output([str(objdump), '-dr', str(elf)], text=True)
    (a.out / 'disassembly.txt').write_text(disassembly)
    k = Kernel(elf); prior = None; frames = []; max_stack = 0; tested = 0
    evidence = json.loads((ROOT / 'analysis/body581-verification.json').read_text())
    for g in range(905, 958):
        gp, rp = a.data / f'frame{g}.geometry', a.data / f'frame{g}.raw'
        for p in (gp, rp): assert sha(p) == evidence['inputs'][p.name]
        arrays = encode(gp.read_bytes(), rp.read_bytes(), g)[2]
        blocks = encode_rows(arrays, prior)
        assert canonical(restore_rows(blocks, list(map(len, arrays)), prior)) == canonical(arrays)
        old = list(prior[0]) if prior is not None else [0] * len(arrays[0])
        total = 0; mode_counts = {}; rows = []
        for b in blocks:
            if b[0]: continue
            ok, got, instructions, stack = k.call(old, b, len(arrays[0]), len(prior[0]) if prior is not None else 0)
            at = int.from_bytes(b[2:4], 'little')
            expected = old + [0x55aa] * (1056 - len(old))
            expected[at:at + 33] = arrays[0][at:at + 33]
            assert ok == 1 and got == expected
            old = got[:len(arrays[0])]
            rows.append(instructions); total += instructions; tested += 1
            max_stack = max(max_stack, stack)
            mode_counts[str(b[1])] = mode_counts.get(str(b[1]), 0) + 1
        assert old == arrays[0]
        frames.append(dict(generation=g, rows=len(rows), instructions=total,
                           min_row_instructions=min(rows), max_row_instructions=max(rows), modes=mode_counts))
        prior = arrays
    old = list(range(1056)); next_row = old[1:33] + [1000]
    good = row_block(next_row, old, 0, 1)
    bad = []
    def change(offset, value):
        b = bytearray(good); b[offset] = value; return bytes(b)
    bad += [('short_header', good[:5], 1056, 1), ('bad_section', change(0, 1), 1056, 1),
            ('bad_mode', change(1, 9), 1056, 1), ('unaligned', change(2, 1), 1056, 1),
            ('short_count', change(4, 32), 1056, 1), ('out_of_range', good, 32, 1),
            ('capacity', good, 1057, 1), ('no_base', good, 1056, 0),
            ('shift_zero', change(6, 0), 1056, 1), ('shift_two', change(6, 2), 1056, 1),
            ('high_mask', change(11, 3), 1056, 1), ('edge_without_literal', good[:11] + b'\0', 1056, 1),
            ('truncated_literal', good[:-1], 1056, 1), ('trailing_byte', good + b'\0', 1056, 1),
            ('invalid_last_value', good[:-1] + b'\x80', 1056, 1)]
    neg = []
    bad = [(label, b, count, 1056 if have else 0) for label, b, count, have in bad]
    bad += [('new_row_outside_base', good, 1056, 32), ('invalid_base_count', good, 1056, 1057)]
    for label, b, count, base_count in bad:
        ok, got, instructions, stack = k.call(old, b, count, base_count)
        assert ok == 0 and got == old, label
        neg.append(label); max_stack = max(max_stack, stack)
    positives = []
    for at in (0, 1023):
        for shift in (-1, 0, 1):
            v = [old[at + i + shift] if 0 <= i + shift < 33 else 123 for i in range(33)]
            b = row_block(v, old, at, shift)
            ok, got, _, stack = k.call(old, b, 1056, 1056)
            want = old.copy(); want[at:at + 33] = v
            assert ok and got == want
            positives.append([at, shift]); max_stack = max(max_stack, stack)
    stack_usage = '\n'.join(line.rsplit(':', 1)[-1] for p in a.out.glob('*.su')
                            for line in p.read_text(encoding='utf8').splitlines())
    report = dict(stage=583, passed=True, product_linked=False, text_B=k.text,
        allocated_sections=k.alloc, compiler=version.splitlines()[0], stack_usage=stack_usage,
        observed_stack_B=max_stack, source_SHA256=sha(source), ELF_SHA256=sha(elf),
        checker_SHA256=sha(Path(__file__)), row_reference_SHA256=sha(ROOT/'tools/nes_row583.py'),
        body581_SHA256=sha(ROOT/'analysis/body581-verification.json'), frames=frames,
        actual_rows=tested, positive_boundaries=positives, atomic_rejections=neg,
        net_Flash_B=None, cycles=None, physical_ms=None,
        limits='Standalone M4 instructions; no product linker deletion, CRC/semantic/epoch wrapper, IRQ/ROM, 65816 or timing proof. Invalid row never commits; partial frame needs outer invalidation.')
    (a.out/'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({x: report[x] for x in ('passed','text_B','observed_stack_B','actual_rows','atomic_rejections')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('data','cc','out'): p.add_argument('--'+name, type=Path, required=True)
    run(p.parse_args())
