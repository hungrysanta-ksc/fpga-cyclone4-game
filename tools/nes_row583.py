# SPDX-License-Identifier: MIT
"""Bounded same-row base addressing. Reference ABI, not product firmware."""
import struct
from nes_abi582 import block, input_blocks, restore


def row_block(values, base, at, shift):
    assert len(values) == 33 and at % 33 == 0 and shift in (-1, 0, 1)
    mask = sum((not 0 <= i + shift < 33 or
                values[i] != base[at + i + shift]) << i for i in range(33))
    body = (bytes([shift & 255]) if shift else b'') + mask.to_bytes(5, 'little')
    body += b''.join(v.to_bytes(2, 'little') for i, v in enumerate(values) if mask >> i & 1)
    return struct.pack('<BBHH', 0, 4 if shift else 3, at, 33) + body


def encode_rows(arrays, previous):
    assert len(arrays[0]) % 33 == 0
    result = []
    for at in range(0, len(arrays[0]), 33):
        values = arrays[0][at:at + 33]
        candidates = [block(0, 0, at, values, [])]
        if previous is not None and at + 33 <= len(previous[0]):
            candidates += [row_block(values, previous[0], at, s) for s in (0, -1, 1)]
        result.append(min(candidates, key=len))
    result += [b for b in input_blocks(arrays, previous) if b[0] != 0]
    return result


def restore_rows(blocks, counts, previous):
    # Independent reference of source-address bounds; reuse582 for other sections.
    result = []
    other = []
    for b in blocks:
        if b[0] != 0:
            other.append(b)
            continue
        k, mode, at, n = struct.unpack_from('<BBHH', b)
        assert at == len(result) and at % 33 == 0 and n == 33 and at + n <= counts[0]
        if mode == 0:
            assert len(b) == 72
            values = list(struct.unpack('<33H', b[6:]))
        else:
            assert mode in (3, 4) and previous is not None
            assert at + n <= len(previous[0])
            shift = int.from_bytes(b[6:7], 'little', signed=True) if mode == 4 else 0
            assert mode == 3 or shift in (-1, 1)
            pos = 7 if mode == 4 else 6
            assert len(b) >= pos + 5
            mask = int.from_bytes(b[pos:pos + 5], 'little'); pos += 5
            assert mask >> 33 == 0 and len(b) == pos + 2 * mask.bit_count()
            values = []
            for i in range(n):
                if mask >> i & 1:
                    values.append(int.from_bytes(b[pos:pos + 2], 'little')); pos += 2
                else:
                    assert 0 <= i + shift < 33 and at + i + shift < len(previous[0])
                    values.append(previous[0][at + i + shift])
        assert all(0 <= v < 32768 for v in values)
        result += values
    assert len(result) == counts[0]
    tail = restore(other, [0] + counts[1:], previous)
    return [result] + tail[1:]
