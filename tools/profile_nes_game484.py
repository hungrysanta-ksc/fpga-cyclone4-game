# SPDX-License-Identifier: MIT
"""Actual482 linked M4 planner profile on71 pinned game snapshots.

Counts executed target instructions by function/source line, not cycles. Input
encoder, writer/DMA/ROM/IRQ completion and isolated128KiB RAM are test models.
Also classifies prior480 actual-RTL E8 replies; not new482 live/physical timing.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
from check_nes_game478 import Machine, encode, crc
from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
for n in ['arm', 'dataset', 'reference', 'live', 'out']:
    p.add_argument('--'+n, required=True, type=Path)
p.add_argument('--preparation', type=Path, help='484 candidate source manifest; absent means exact482 baseline')
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=False)
reference = json.loads((a.reference/'result.json').read_text(encoding='utf8'))
selected = json.loads((ROOT/'analysis/mmc482-verification.json').read_text(encoding='utf8'))
assert reference['passed']
if a.preparation:
    prepared = json.loads(a.preparation.read_text(encoding='utf8'))
    assert prepared['baseline_firmware_SHA256'] == selected['ARM']['firmware_SHA256']
    for n, h in prepared['baseline_sources'].items():
        assert sha(a.arm/n) == prepared['patch_sources'].get(n, h), n
else:
    assert sha(a.arm/'obj-nes-100/firmware.stm') == selected['ARM']['firmware_SHA256']
nums = list(map(int, re.search(r'\{(.*?)\}', (a.arm/'nes_palette165.inc').read_text(encoding='utf8'), re.S)[1].split(',')))
palette = struct.pack('<64H', *nums)
assert hashlib.sha256(palette).hexdigest() == reference['palette_sha256']
functions, lines = [], []
with (a.arm/'obj-nes-100/sd2snes.elf').open('rb') as f:
    elf = ELFFile(f)
    for s in elf.get_section_by_name('.symtab').iter_symbols():
        if s['st_info']['type'] == 'STT_FUNC' and s['st_size']:
            functions.append((s['st_value'] & ~1, s['st_size'], s.name))
    dwarf = elf.get_dwarf_info()
    for cu in dwarf.iter_CUs():
        table = dwarf.line_program_for_CU(cu)
        if not table:
            continue
        for entry in table.get_entries():
            state = entry.state
            if state:
                name = table['file_entry'][state.file-1].name.decode() if not state.end_sequence else ''
                lines.append((state.address, name.rsplit('/', 1)[-1], state.line or 0))
functions.sort()
lines.sort()
starts, line_starts = [x[0] for x in functions], [x[0] for x in lines]

class ProfileMachine(Machine):
    def __init__(self, src, palette):
        self.collect = False
        self.pc_counts = Counter()
        self.plan_events = []
        super().__init__(src, palette)
    def call(self, name, args):
        old = self.collect
        self.collect = name == 'nes_native_video211_plan'
        try:
            return super().call(name, args)
        finally:
            self.collect = old
    def hook(self, cpu, at, size, user):
        if self.collect and at not in [self.end, self.spi, self.writer]:
            self.pc_counts[at] += 1
        elif self.collect and at == self.writer:
            from unicorn.arm_const import UC_ARM_REG_R2
            q = bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R2), 40))
            self.plan_events.append({'prefix_instructions': sum(self.pc_counts.values()), 'kind': q[6]})
        super().hook(cpu, at, size, user)

def attribute(counts):
    fn, source = Counter(), Counter()
    for pc, count in counts.items():
        i = bisect_right(starts, pc)-1
        name = functions[i][2] if i >= 0 and pc < functions[i][0]+functions[i][1] else '<unknown>'
        fn[name] += count
        i = bisect_right(line_starts, pc)-1
        if i >= 0 and lines[i][1]:
            source[f'{lines[i][1]}:{lines[i][2]}'] += count
        else:
            source['<unknown>'] += count
    return fn, source

m = ProfileMachine(a.arm, palette)
frames, all_pcs, inputs = [], Counter(), {}
for serial, frame in enumerate(range(905, 976), 1):
    files = [a.dataset/f'frame{frame}.{ext}' for ext in ['geometry', 'raw']]
    for q in files:
        assert sha(q) == reference['input_sha256'][q.name]
        inputs[q.name] = sha(q)
    geometry, raw = [q.read_bytes() for q in files]
    packets, counts, _ = encode(geometry, raw, frame & 65535)
    m.pc_counts.clear()
    m.plan_events.clear()
    actual = m.frame(packets, geometry, raw, frame & 65535, serial)
    prior = json.loads((a.reference/f'frame{frame}.json').read_text(encoding='utf8'))['candidate']
    assert actual['state_sha256'] == prior['state_sha256'] and actual['plans'] == prior['plans'], frame
    assert actual['receive_instructions'] == prior['receive_instructions']
    if not a.preparation:
        assert actual['planner_instructions'] == prior['planner_instructions']
    assert sum(m.pc_counts.values()) == actual['planner_instructions']
    fn, source = attribute(m.pc_counts)
    all_pcs.update(m.pc_counts)
    row = {'frame': frame, 'planner_instructions': actual['planner_instructions'],
           'receive_instructions': actual['receive_instructions'], 'plan_count': len(actual['plans']),
           'state_SHA256': actual['state_sha256'], 'functions': dict(fn.most_common()),
           'baseline_planner_instructions': prior['planner_instructions'],
           'saved_instructions': prior['planner_instructions']-actual['planner_instructions'],
           'plan_ready_events': [dict(e) for e in m.plan_events],
           'source_lines_top30': dict(source.most_common(30))}
    (a.out/f'frame{frame}.json').write_text(json.dumps(row, indent=2)+'\n', encoding='utf8')
    frames.append(row)
    if serial in [1, 20, 40, 60, 71]:
        print(json.dumps({'profiled': serial, 'last_frame': frame}), flush=True)
fn, source = attribute(all_pcs)

# These are real SPI request/reply bytes from prior480 transaction RTL. Check
# CRC/ABI, but do not infer busy duration or physical game-run proportions.
e8, wires = Counter(), {}
for q in sorted(a.live.glob('H-*.req')):
    wire = q.read_bytes()
    if len(wire) < 9 or wire[0] != 1 or wire[8] != 0xe8:
        continue
    rx = q.with_suffix('.rsp').read_bytes()
    assert len(rx) == 20 and rx[1:3] == b'\xd7\x04' and crc(rx[1:19], 8, 7, 0) == rx[19]
    assert rx[6] in [0, 1] and rx[18] == 0
    if rx[6]:
        kind = 'descriptor_ready'
    else:
        assert not any(rx[7:18])
        kind = {0:'busy_empty', 1:'credit_empty', 2:'finished_empty', 6:'retire_pending_empty'}.get(rx[3])
        assert kind, rx.hex()
    e8[kind] += 1
    wires[q.name] = {'request': sha(q), 'reply': sha(q.with_suffix('.rsp'))}
assert sum(e8.values()) > 0
result = {'passed': True, 'scope': __doc__, 'firmware_SHA256': sha(a.arm/'obj-nes-100/firmware.stm'),
          'ELF_SHA256': sha(a.arm/'obj-nes-100/sd2snes.elf'), 'frames': frames,
          'planner_instructions': sum(all_pcs.values()), 'exclusive_functions': dict(fn.most_common()),
          'source_lines_top60': dict(source.most_common(60)), 'input_SHA256': inputs,
          'palette_SHA256': hashlib.sha256(palette).hexdigest(),
          'E8_prior480_status_counts': dict(e8), 'E8_prior480_wire_SHA256': wires,
          'baseline_planner_instructions': sum(q['baseline_planner_instructions'] for q in frames),
          'saved_instructions': sum(q['saved_instructions'] for q in frames),
          'preparation_SHA256': sha(a.preparation) if a.preparation else None,
          'state_and_plan_equality_to478': True, 'physical_FPS': None,
          'limits': ['Target instructions, not hardware cycles or full ARM/IRQ/ROM timeline',
                     '71 historical game snapshots, not the482 hardware run or same-scene replay',
                     'Synthetic SPI and immediate writer completion; isolated unit RAM is not target RAM budget',
                     'E8 classification from prior480 actual RTL transaction trace, not new482 live timing',
                     'No new Quartus or physical hardware test']}
(a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
print(json.dumps({'passed': True, 'instructions': result['planner_instructions'],
                  'functions': dict(fn.most_common(8)), 'E8': dict(e8)}))
