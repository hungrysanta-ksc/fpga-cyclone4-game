"""Build a private static SNES test from a 144x160 GBC RGB555 capture.

The extra BG2 tile planes return the low four component bits through additive
color math. No captured game data is stored in Git or the board update.
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/renderer"))
from build_gbc_product_renderer import Asm, dma


def schedule(image):
    colors = list(dict.fromkeys([0, *map(int, image.flat)]))
    color_id = {c: i for i, c in enumerate(colors)}
    rows = [{color_id[int(c)] for c in row} for row in image]
    future = np.full((145, len(colors)), 255, dtype=np.uint8)
    for y in reversed(range(144)):
        future[y] = future[y + 1]
        future[y, list(rows[y])] = y
    slots = {i: i for i in range(min(64, len(colors)))}
    initial = (colors + [0] * 64)[:64]
    tiles = np.empty_like(image, dtype=np.uint8)
    events = [[] for _ in rows]
    for y, row in enumerate(rows):
        if y:
            incoming = sorted(
                set(range(len(colors))) - slots.keys(), key=lambda i: (future[y, i], i))
            outgoing = sorted(slots.keys() - {0}, key=lambda i: (-int(future[y, i]), i))
            for new, old in list(zip(incoming, outgoing))[:7]:
                if future[y, new] >= future[y, old]:
                    break
                slot = slots.pop(old)
                slots[new] = slot
                events[y-1].append((slot, colors[new]))
        if not row <= slots.keys():
            raise ValueError(f"row {y} exceeds the seven-channel schedule")
        tiles[y] = [slots[color_id[int(c)]] for c in image[y]]
    return initial, tiles, events


def planar(image, planes):
    data = bytearray()
    for top in range(0, 144, 8):
        for left in range(0, 160, 8):
            tile = image[top:top+8, left:left+8]
            for pair in range(0, planes, 2):
                for row in tile:
                    for plane in (pair, pair+1):
                        data.append(int(np.packbits((row >> plane) & 1)[0]))
    return data


def hardware_output(prefix):
    def words(ext):
        return np.loadtxt(str(prefix) + ext, dtype=np.uint16, converters=lambda s: int(s, 16))
    # FPGA words are ordered by plane pair, fine Y, tile row, tile column.
    planes = words('.planes').reshape(3, 8, 18, 20).transpose(0, 2, 1, 3)
    indices = np.zeros((144, 160), dtype=np.uint8)
    for pair in range(3):
        for bit in range(8):
            w = planes[pair].reshape(144, 20)
            indices[:, bit::8] |= ((w >> (7-bit) & 1) << (2*pair)).astype(np.uint8)
            indices[:, bit::8] |= ((w >> (15-bit) & 1) << (2*pair+1)).astype(np.uint8)
    packed = words('.low')
    residual = np.stack([packed >> (4*i) & 15 for i in range(4)], axis=1).reshape(144, 160)
    rows = np.loadtxt(str(prefix) + '.pal', dtype=int, ndmin=2)
    if len(rows) < 64 or not np.all(rows[:64, 0] == -1) or not np.array_equal(rows[:64, 1], np.arange(64)):
        raise ValueError("incomplete initial palette")
    initial = rows[:64, 2].tolist()
    events = [[] for _ in range(144)]
    for y, slot, color in rows[64:]:
        if not (0 <= y < 143 and 0 < slot < 64 and 0 <= color < 32768 and len(events[y]) < 7):
            raise ValueError("invalid palette event")
        events[y].append((int(slot), int(color)))
    return initial, indices, events, residual


def build(pixels, hardware=None):
    if pixels.shape != (144, 160) or pixels.min() < 0 or pixels.max() > 32767:
        raise ValueError("expected 160x144 RGB555")
    # One low red bit, two green, one blue. Carries cannot cross components.
    residual = (pixels & 1) | ((pixels >> 4) & 6) | ((pixels >> 7) & 8)
    palette = [(n & 1) | ((n & 6) << 4) | ((n & 8) << 7) for n in range(16)]
    base = pixels & (0x7fff ^ (1 | 3 << 5 | 1 << 10))
    assert np.array_equal(base + np.array(palette)[residual], pixels)
    if hardware is None:
        initial, indices, events = schedule(base)
    else:
        initial, indices, events, residual = hardware_output(hardware)
        live = np.array(initial)
        for y in range(144):
            if not np.array_equal(live[indices[y]] + np.array(palette)[residual[y]], pixels[y]):
                raise ValueError(f"RTL RGB555 mismatch on line {y}")
            for slot, color in events[y]:
                live[slot] = color
    rom = bytearray(131072)
    a = Asm(0x8000)
    a.emit(0x78, 0x18, 0xfb, 0xc2, 0x10)
    a.ldx16(0x1fff)
    a.emit(0x9a)
    a.write(0x2100, 0x80)
    for reg in (0x4200, 0x420c, 0x212c, 0x212d, 0x2133):
        a.stz(reg)
    def put(offset, data):
        rom[offset:offset+len(data)] = data
        return ((offset//32768)<<16) | 0x8000 | (offset % 32768)
    def vram(offset, dest, data):
        a.write(0x2115, 0x80)
        a.write(0x2116, dest & 255)
        a.write(0x2117, dest >> 8)
        dma(a, put(offset, data), len(data), 1, 0x18)
    # Each BG has an explicit all-zero border tile.
    vram(0x8000, 0, planar(indices, 8) + bytes(64))
    vram(0x10000, 0x4000, planar(residual, 4) + bytes(32))
    for layer, attr in enumerate((0, 4 << 10)):
        tilemap = bytearray()
        for y in range(32):
            for x in range(32):
                tile = (y-5)*20+x-6 if 5<=y<23 and 6<=x<26 else 360
                tilemap += struct.pack('<H', tile | attr)
        vram(0x4000+2048*layer, 0x6000+0x400*layer, tilemap)
    colors = initial + palette
    a.stz(0x2121)
    dma(a, put(0x5000, struct.pack('<80H', *colors)), 160, 0, 0x22)
    for channel in range(7):
        table = bytearray((41, 0, 0, 0, 0))
        for changes in events:
            slot, color = changes[channel] if channel < len(changes) else (0, 0)
            table.extend((1, slot, slot, color & 255, color >> 8))
        table.append(0)
        address = put(0x2400+channel*0x300, table)
        reg = 0x4300 + channel*16
        for off, v in enumerate((3, 0x21, address & 255, address >> 8 & 255, 0)):
            a.write(reg+off, v)
    for reg, val in ((0x2105,3),(0x2107,0x60),(0x2108,0x64),(0x210b,0x40),
                     (0x212c,1),(0x212d,2),(0x2130,2),(0x2131,0x21)):
        a.write(reg,val)
    for reg in (0x210d,0x210f):
        a.stz(reg)
        a.stz(reg)
        a.write(reg+1,0xff)
        a.write(reg+1,3)
    a.write(0x2132, 0xe0)
    a.write(0x420c, 127)
    a.write(0x2100,15)
    # Restore initial colors every VBlank before the next HDMA table starts.
    a.label('wait_visible')
    a.read(0x4212)
    a.branch(0x30, 'wait_visible')
    a.label('wait_blank')
    a.read(0x4212)
    a.branch(0x10, 'wait_blank')
    a.stz(0x2121)
    dma(a, 0xd000, 128, 0, 0x22)
    a.jump('wait_visible')
    put(0,a.finish())
    put(0x7fc0,b'GBC RGB555 PROBE'.ljust(21))
    put(0x7fd5,bytes((0x20,0,7,0,1,0,0)))
    put(0x7ffc,struct.pack('<H',0x8000))
    return rom


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--hardware', type=Path, help='Questa +EXPORT file prefix')
    args = parser.parse_args()
    args.output.write_bytes(build(np.load(args.capture, allow_pickle=False), args.hardware))
