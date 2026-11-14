"""Build a private SNES replay from verified GBC774 Questa +EXPORT output.

For a LoROM emulator, only cartridge I/O replies are substituted. The renderer
boots normally and uses its production IRQ, metadata copy, DMA and menu code.
"""
import argparse
import hashlib
import struct
from pathlib import Path


def read_words(path, count):
    words = [int(v, 16) for v in path.read_text().split()]
    if len(words) != count:
        raise ValueError(f"{path} must contain {count} words")
    return struct.pack(f"<{count}H", *words)


def replay(renderer, prefix):
    rom = bytearray(renderer.read_bytes())
    if hashlib.sha256(rom).hexdigest() != "730564d2b2efe60d73ff3aa2bd55b0639fd951480227023303909c8bf448af1c":
        raise ValueError("expected the verified GBC774 renderer")
    replies = {0x6000: 0xc3, 0x6007: 0xb0, 0x6002: 0x0a, 0x600c: 0, 0x600d: 0x20}
    for addr, value in replies.items():
        op = struct.pack("<BH", 0xad, addr)
        for start, end in ((0x100,0x2100),(0x3000,0x4600),(0x4800,0x5000),(0x6000,0x7000)):
            rom[start:end] = rom[start:end].replace(op, bytes((0xa9,value,0xea)))
    rom.extend(b"\xff" * (0x400000-len(rom)))
    rom[0x7fd7] = 12
    rom[0x200000:0x204380] = read_words(prefix.with_suffix(".planes"), 8640)
    rom[0x208000:0x20ad00] = read_words(prefix.with_suffix(".low"), 5760)
    records = [tuple(map(int,line.split())) for line in prefix.with_suffix(".pal").read_text().splitlines()]
    if [(row,slot) for row,slot,_ in records[:64]] != [(-1,i) for i in range(64)]:
        raise ValueError("incomplete initial palette")
    rom[0x204400:0x204480] = struct.pack("<64H", *(rgb for _,_,rgb in records[:64]))
    channels = [[] for _ in range(143)]
    for row, slot, rgb in records[64:]:
        if not (0 <= row < 143 and 0 < slot < 64 and 0 <= rgb < 32768 and len(channels[row]) < 7):
            raise ValueError("invalid HDMA palette event")
        channels[row].append((slot,rgb))
    for i in range(7):
        previous = 0
        data = bytearray((1,0,0,0,0))
        for row, changes in enumerate(channels):
            if len(changes) <= i:
                continue
            target = 41+row
            while target-previous > 127:
                data[-5] = 127
                data.extend((1,0,0,0,0))
                previous += 127
            data[-5] = target-previous
            slot, rgb = changes[i]
            data.extend((1,slot,slot,rgb & 255,rgb >> 8))
            previous = target
        data.append(0)
        if len(data) > 726:
            raise ValueError("HDMA stream exceeds page allocation")
        struct.pack_into("<H", rom, 0x204480+2*i, len(data))
        start = 0x204600+0x300*i
        rom[start:start+len(data)] = data
    return rom


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("renderer","prefix","output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    args.output.write_bytes(replay(args.renderer,args.prefix))
