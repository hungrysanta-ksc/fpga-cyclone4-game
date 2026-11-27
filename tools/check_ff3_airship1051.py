"""Replay the same CHR writes and captured scenes on both linked planners."""
import argparse
import csv
import json
import struct
from collections import Counter
from pathlib import Path

from check_ff3_backdrop1046 import captured, layouts
from check_ff3_battle1047 import replay, runtime_modes
from check_ff3_sd1043 import Machine, fat16
from elftools.elf.elffile import ELFFile


def check_headers(src):
    receiver, header = 0x21000000, 0x21004000
    machine = Machine(src, fat16())
    machine.u.mem_map(receiver, 0x5000)
    rx, = layouts(src, ('nes_native165',))
    for board, version, flags, expected in (
        *((0x7d, 0x2235, g << 1, 256 + g) for g in range(64)),
        (0x7d, 0x2234, 0, 255), (0x7d, 0x2234, 511, 0),
        (0x7c, 0x2234, 0, 0), (0x7c, 0x2235, 0, None),
        (0x7d, 0x2235, 1, None), (0x7d, 0x2235, 128, None),
        (0x7d, 0x2235, 256, None), (0x7d, 0x2236, 0, None),
    ):
        machine.u.mem_write(machine.sym['nes_board_id'], bytes([board]))
        machine.call('nes_native165_reset',receiver)
        word = (version << 48) | (1 << 42) | (1 << 36) | (224 << 28) | (flags << 3)
        machine.u.mem_write(header, struct.pack('>HHQ',0xe000,1,word))
        accepted = machine.call('nes_native165_packet',receiver,0,header,12)
        assert bool(accepted) == (expected is not None)
        if accepted:
            assert int.from_bytes(machine.u.mem_read(receiver+rx['dirty_chr'],2),'little') == expected


def compare(old, new, log, writes, strides=(1,3)):
    with writes.open() as stream:
        tiles = {int(r['frame']): {int(t) for t in r['touched_tiles'].split(',') if t}
                  for r in csv.DictReader(stream, delimiter='\t')}
    groups={f:{t>>3 for t in touched} for f,touched in tiles.items()}
    frames = list(captured(log))
    assert frames and all(b[0] == a[0] + 1 for a, b in zip(frames, frames[1:]))
    pages = {f: 255 ^ sum(1 << p for p in {g >> 3 for g in groups[f]}) for f, _ in frames}
    history = {f: mask == 255 for f, mask in pages.items()}
    result = {}
    for stride in strides:
        profile = stride == 1
        samples = {frames[-1][0]: Counter()} if profile else {}
        rows = [replay(src, frames, history, True, stride, pages=pages, written_groups=scope,
                       profile=profile, instruction_samples=samples if scope is not None else None,
                       touched_tiles=tiles)
                for src, scope in ((old, None), (new, None), (new, groups))]
        assert all({k:v for k,v in a.items() if k!='planner_instructions'} ==
                   {k:v for k,v in b.items() if k!='planner_instructions'}
                   for a,b in zip(rows[0], rows[1], strict=True)), 'legacy page receipt changed'
        for a, b in zip(rows[0], rows[2], strict=True):
            assert (a['f'], a['image']) == (b['f'], b['image'])
        keys = ('f','commands','descriptor_bytes','tile_bytes') + (('planner_instructions',) if profile else ())
        result[str(stride)] = {mode: [{k:r[k] for k in keys}
                                     for r in data] for mode, data in zip(('page','group'), (rows[0],rows[2]))}
        if samples:
            counts=samples[frames[-1][0]].copy()
            totals=Counter()
            with (new/'obj-nes-100/sd2snes.elf').open('rb') as file:
                symbols=ELFFile(file).get_section_by_name('.symtab')
                for sym in symbols.iter_symbols():
                    if sym['st_info']['type']!='STT_FUNC':continue
                    begin=sym['st_value']&~1
                    hits=sum(counts.pop(pc,0) for pc in range(begin,begin+sym['st_size'],2))
                    if hits:totals[sym.name]+=hits
            totals['unattributed']=sum(counts.values())
            assert sum(totals.values())==rows[2][-1]['planner_instructions']
            result['last_frame_planner_instructions']=dict(totals.most_common())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('old', 'new', 'work'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    work = args.work
    check_headers(args.new)
    runtime_modes(args.new, page_history=True)
    results = {}
    for scene, log, writes in (
        ('hover', work/'rtl14/14.log', work/'air/chr-tiles.tsv'),
        ('flight', work/'rtl48/48.log', work/'air/chr-tiles.tsv'),
        ('town', work.parent/'nes-ff3-1049/town-rtl/703.log', work/'walk/chr-tiles.tsv'),
        ('field', work.parent/'nes-ff3-1049/field-rtl/1018.log', work/'walk/chr-tiles.tsv'),
    ):
        results[scene] = compare(args.old, args.new, log, writes)
        print(scene, results[scene]['1']['page'][-1], results[scene]['1']['group'][-1], flush=True)
    (work/'comparison.json').write_text(json.dumps(results, indent=2)+'\n')
    cruise=compare(args.old,args.new,work/'rtl40/40.log',work/'cruise/chr-tiles.tsv',strides=(4,5))
    (work/'cruise-comparison.json').write_text(json.dumps(cruise, indent=2)+'\n')
