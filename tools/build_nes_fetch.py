"""Original NROM pattern-table switching diagnostic. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse
import hashlib
import json


def build(out):
    out.mkdir(parents=True, exist_ok=False)
    code = bytearray()
    labels, fixups = {}, []
    def emit(*values): code.extend(values)
    def label(name): labels[name] = 0x8000 + len(code)
    def branch(op, name):
        emit(op, 0)
        fixups.append((len(code)-1, name, True))
    def jump(name):
        emit(0x4c, 0, 0)
        fixups.append((len(code)-2, name, False))
    def lda(value): emit(0xa9, value)
    def sta(address): emit(0x8d, address & 255, address >> 8)
    emit(0x78, 0xd8, 0xa2, 0xff, 0x9a)  # SEI CLD LDX #FF TXS
    lda(0)
    for address in (0x2000, 0x2001, 0x4010, 0x4015, 0, 1): sta(address)
    for name in ('wait1', 'wait2'):
        label(name); emit(0x2c, 2, 0x20); branch(0x10, name)  # BIT PPUSTATUS / BPL
    lda(0x3f); sta(0x2006); lda(0); sta(0x2006)
    for value in [0x0f, 0x21, 0x30, 0x16]*8:
        lda(value); sta(0x2007)
    lda(0x20); sta(0x2006); lda(0); sta(0x2006)
    emit(0xa0, 4, 0xa2, 0)  # LDY #4 LDX #0
    label('nt'); emit(0x8a); sta(0x2007)  # TXA: tiles 0..255 repeated, also attributes
    emit(0xe8); branch(0xd0, 'nt'); emit(0x88); branch(0xd0, 'nt')
    lda(0); sta(0x2003); emit(0xa2, 0); lda(0xff)
    label('oam'); sta(0x2004); emit(0xe8); branch(0xd0, 'oam')
    lda(0); sta(0x2005); sta(0x2005); lda(0x0a); sta(0x2001)
    label('main'); emit(0x2c, 2, 0x20); branch(0x10, 'main')
    emit(0xa5, 0, 0x49, 0x10, 0x85, 0); sta(0x2000)  # toggle BG table only
    lda(0); sta(0x2005); sta(0x2005); emit(0xe6, 1)
    # Reading status above clears vblank, so main waits for the next edge.
    jump('main')
    for pos, name, relative in fixups:
        target = labels[name]
        if relative:
            delta = target-(0x8000+pos+1)
            assert -128 <= delta <= 127
            code[pos] = delta & 255
        else: code[pos:pos+2] = target.to_bytes(2, 'little')
    prg = bytearray([0xea])*32768
    prg[:len(code)] = code
    for pos in (0x7ffa, 0x7ffc, 0x7ffe): prg[pos:pos+2] = (0x8000).to_bytes(2, 'little')
    tiles = []
    for index in range(512):
        tile = bytearray(hashlib.sha256(b'Original NES fetch 005\0'+index.to_bytes(2,'little')).digest()[:16])
        tile[:2] = index.to_bytes(2, 'little')
        tiles.append(bytes(tile))
    assert len(set(tiles)) == 512
    chrdata = b''.join(tiles)  # NES: eight low-plane bytes followed by eight high-plane bytes
    rom = b'NES\x1a'+bytes([2,1])+bytes(10)+prg+chrdata
    (out/'fetch.nes').write_bytes(rom)
    for name, data in [('prg',prg), ('chr',chrdata)]:
        (out/(name+'.hex')).write_text(''.join(f'{b:02x}\n' for b in data),encoding='utf-8',newline='\n')
    manifest = dict(candidate='NES-P2-FETCH-005',license='MIT',original_diagnostic=True,mapper=0,
        prg_bytes=len(prg),chr_bytes=len(chrdata),code_bytes=len(code),unique_tiles=512,
        sha256=hashlib.sha256(rom).hexdigest(),builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='NROM PPUCTRL BG pattern-table switch every vblank, zero scroll, BG only; not MMC3 or RTL execution',
        palette_indices=[15,33,48,22],labels=labels)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    return manifest

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    print(json.dumps(build(p.parse_args().out),indent=2))
