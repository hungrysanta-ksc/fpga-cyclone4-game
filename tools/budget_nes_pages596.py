"""Price unchanged 595 typed blocks and verify candidate envelopes on pinned captures."""
import argparse
import json
import struct
import zipfile
from hashlib import sha256
from pathlib import Path

from analyze_nes_boundary592 import WIDTH, raster_next, restore
from check_nes_game478 import encode, sha
from check_nes_receiver593 import Receiver
from check_nes_ack593 import Display

ROOT = Path(__file__).resolve().parents[1]


def blocks(arrays):
    for kind, values in enumerate(arrays[1:], 1):
        for start in range(0, len(values), 32):
            group = values[start:start+32]
            n = len(group)
            repeat = kind not in (1, 5) and n >= (10 if kind == 6 else 2) and len(set(group)) == 1
            linear = (kind == 4 and n >= 2 and group[0] >> 49 == 0 and
                      all(b == raster_next(a) for a, b in zip(group, group[1:])))
            mode = 2 if linear else int(repeat)
            header = struct.pack('<BH', kind | mode << 3, n)
            body = b''.join(v.to_bytes(WIDTH[kind], 'little') for v in (group[:1] if mode else group))
            yield header + body, 3 + n * WIDTH[kind]


def pages(records, policy):
    """Input contains one phase. Reserve scratch space only for the active block."""
    out = []
    current = b''
    for record, worst in records:
        room = worst if policy == 'reserve' else len(record)
        if current and (policy == 'single' or len(current) + room > 252):
            out.append(current)
            current = b''
        assert len(current) + room <= 252
        current += record
    if current:
        out.append(current)
    return out


def sections(records, policy):
    return [pages([r for r in records if (r[0][0] & 7 == 6) == raw], policy) for raw in (False, True)]


class Packed(Receiver):
    def tail(self):
        start = len(self.packets)
        super().tail()
        old = self.packets[start:]
        del self.packets[start:]
        for phase, part in enumerate(sections(list(blocks(self.arrays)), 'reserve'), 2):
            marker = [p for p in old if p[0] == phase][-1][-8:]
            for ordinal, body in enumerate(part + [marker]):
                self.packets.append(bytes([phase, ordinal]) + body)
        self.packets.append(old[-1])


def check_arm(arm, frames):
    receiver = Packed(arm)
    for g in (905, 906):
        receiver.setup(*frames[g], g)
        assert receiver.checked_frame()['ok']
    receiver.setup(*frames[907], 907)
    for _ in range(100):
        assert receiver.call('nes_native165_poll', [receiver.state, receiver.spi | 1, 0])
        if receiver.get('r_phase') == 2 and receiver.get('r_ord') > 0:
            break
    else:
        raise AssertionError('partial packed metadata not reached')
    assert not receiver.get('r_base')
    receiver.call('nes_native165_reset', [receiver.state])
    receiver.set('r_epoch', 1, 4)
    receiver.toggle = receiver.token = receiver.serial = 0
    receiver.previous = None
    receiver.setup(*frames[905], 905, fault='repair_once', cold=True)
    repaired = receiver.checked_frame()
    assert repaired['ok'] and repaired['repairs'] == 1 and receiver.get('r_seen',4) == (1 << 29) - 1
    modes = []
    for mode in ('normal', 'wrong_final_ACK', 'STOP_at_EA'):
        runtime = Display(arm, False, 400)
        runtime.setup_trial(*frames[905], mode)
        source = Packed.__new__(Packed)
        source.__dict__.update(runtime.source_model.__dict__)
        runtime.source_model = source
        for _ in range(250):
            ok = runtime.call('nes_runtime165_step', [runtime.rt])
            if not ok or runtime.saw_ea:
                break
        assert runtime.saw_seal and bool(ok) == (mode == 'normal')
        assert runtime.saw_ea == (mode != 'wrong_final_ACK')
        count = runtime.get(runtime.rt,'nes_native_runtime165','frames',4)
        assert count == int(mode != 'wrong_final_ACK') and runtime.state_value() == (0 if ok else 4)
        modes.append(dict(mode=mode, displayed=count, EA=runtime.saw_ea, state=runtime.state_value()))
    return dict(partial_warm_generation=907, cold_repair_rows=29, final=modes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('arm','archive','maps','out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads((ROOT/'analysis/region595-verification.json').read_bytes())
    assert sha(args.arm/'obj-nes-100/sd2snes.elf') == baseline['ELF']
    pins = json.loads((ROOT/'analysis/body581-verification.json').read_bytes())['inputs']
    frames, costs = {}, []
    previous = []
    with zipfile.ZipFile(args.archive) as z:
        for g in range(905,958):
            geometry, raw = frames[g] = tuple(z.read(f'data/frame{g}.{ext}') for ext in ('geometry','raw'))
            for data, ext in ((geometry,'geometry'),(raw,'raw')):
                assert sha256(data).hexdigest() == pins[f'frame{g}.{ext}']
            arrays = encode(geometry,raw,g)[2] + [list(raw)]
            records = list(blocks(arrays))
            assert restore([r for r,_ in records], list(map(len,arrays)))[1:] == arrays[1:]
            page_counts = {}
            for policy in ('single','reserve','tight'):
                parts = sections(records,policy)
                assert b''.join(b for part in parts for b in part) == b''.join(r for r,_ in records)
                page_counts[policy] = sum(map(len,parts))
            saved = page_counts['single'] - page_counts['reserve']
            row = dict(generation=g, data_pages=page_counts, saved_pages=saved, fixed_calls=3*saved, fixed_wire_B=21*saved)
            if g in (905,906):
                hist = baseline['frames'][g-905]
                groups = len(arrays[0]) // 33
                replies = 0
                for i in range(groups):
                    old, new = previous[33*i:33*i+33], arrays[0][33*i:33*i+33]
                    replies += not (len(old) == 33 and (new == old or new[:-1] == old[1:] or new[1:] == old[:-1]))
                summaries = 0 if g == 905 else 8*groups
                # 32 B BEGIN, three input phase ENDs plus map-summary END and COMMIT.
                bodies = 32 + 5*8 + summaries + 72*replies + sum(len(r) for r,_ in records)
                n = hist['packets']
                assert n == (1 + summaries//240 + 1 + (max(replies,1)+2)//3
                             + page_counts['single'] + 3)
                assert 8*hist['calls'] + 16*len(hist['actions']) + bodies - 3*n == hist['wire_B']
                row['fixed_other_queries'] = dict(calls=hist['calls']-3*saved, wire_B=hist['wire_B']-21*saved,
                                                   packets=n-saved)
            previous = arrays[0]
            costs.append(row)
    maps = json.loads((args.maps/'result.json').read_bytes())
    for name, res in maps.items():
        assert sha(args.maps/name/'region.map.rpt') == res['report']
    screen = baseline['local_screen_LE']
    joint = maps['joint']
    result = dict(stage=596, costs=costs, totals={k:sum(r[k] for r in costs) for k in ('saved_pages','fixed_calls','fixed_wire_B')},
                  data_pages={k:sum(r['data_pages'][k] for r in costs) for k in ('single','reserve','tight')},
                  baseline_LE=baseline['candidate']['LE'], screen_LE=screen,
                  diagnostic_reduction_LE=baseline['candidate']['LE']-joint['LE'],
                  unaccounted_LE=joint['LE']-screen, combination_excess=joint['comb']-screen,
                  diagnostics=maps, ARM=check_arm(args.arm,frames), ELF=baseline['ELF'],
                  scope='53 pinned inputs in reference packing; packed ARM uses modeled peripherals. Diagnostic local MAP, no combined functional RTL or board/phase timing.')
    args.out.write_bytes((json.dumps(result,indent=2)+'\n').encode())


if __name__ == '__main__':
    main()
