"""Offline CHR format/resource probe; no emulator, firmware, or timing approval.

Reads a local iNES image and emits counts/hashes only, never ROM or tile bytes.
Scenario traffic is illustrative, not a measurement of game execution.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def snes_tile(nes_tile, bpp):
    if len(nes_tile) != 16 or bpp not in (2, 4):
        raise ValueError('Requires one NES 2bpp tile and SNES 2/4bpp output')
    first_pair = bytes(v for y in range(8) for v in (nes_tile[y], nes_tile[y+8]))
    return first_pair + bytes(16 if bpp == 4 else 0)


def verify_pixels(nes_tile, converted, bpp):
    for y in range(8):
        for x in range(8):
            mask = 1 << (7-x)
            expected = bool(nes_tile[y] & mask) + 2*bool(nes_tile[y+8] & mask)
            actual = sum(((converted[(p//2)*16+y*2+(p%2)] >> (7-x)) & 1) << p
                         for p in range(bpp))
            if expected != actual:
                raise ValueError('NES/SNES decoded pixel mismatch')


def analyze(path):
    data = path.read_bytes()
    if len(data) < 16 or data[:4] != b'NES\x1a' or data[7] & 0x0c == 0x08:
        raise ValueError('This bounded probe requires iNES 1.0')
    prg_size, chr_size = data[4]*16384, data[5]*8192
    offset = 16 + (512 if data[6] & 4 else 0) + prg_size
    if not chr_size or offset+chr_size != len(data):
        raise ValueError('Requires CHR-ROM and an exact declared file size')
    chr_data = data[offset:]
    tiles = [chr_data[i:i+16] for i in range(0,chr_size,16)]
    for tile in tiles:
        for bpp in (2,4):
            verify_pixels(tile, snes_tile(tile,bpp), bpp)
    # A plane-order error must be visible to the independent pixel decoder.
    asymmetric = bytes([0x80]+[0]*7+[0x01]+[0]*7)
    try:
        verify_pixels(asymmetric, asymmetric, 2)
    except ValueError:
        rejected = True
    else:
        raise AssertionError('Negative plane-order control did not fail')
    regions = [dict(name='BG patterns 1024x16',start=0x0000,size=0x4000),
               dict(name='OBJ patterns 512x32',start=0x4000,size=0x4000),
               dict(name='BG map A 64x32x2',start=0x8000,size=0x1000),
               dict(name='BG map B 64x32x2',start=0x9000,size=0x1000)]
    for left,right in zip(regions,regions[1:]):
        assert left['start']+left['size'] <= right['start']
    assert regions[-1]['start']+regions[-1]['size'] <= 65536
    # Explicitly proposed budgets: not actual register/HDMA ABI sizes.
    base = dict(map_strip=128,full_oam=544,palette=160,registers=32,raster=128,metadata=64)
    scenarios=[]
    for name,bg,obj in [('cached_scroll',0,0),('one_kib_BG_and_OBJ_miss',1024,2048),
                        ('four_kib_BG_and_OBJ_miss',4096,8192)]:
        count=sum(base.values())+bg+obj
        scenarios.append(dict(name=name,proposed_base=base,bg_converted_bytes=bg,
                              obj_converted_bytes=obj,total_bytes=count,
                              payload_only_min_vblanks=math.ceil(count/5632)))
    return dict(kind='offline_chr_layout_and_illustrative_budget_not_game_trace',
                rom_sha256=hashlib.sha256(data).hexdigest(),
                mapper=(data[6] >> 4) | (data[7] & 0xf0),prg_bytes=prg_size,chr_bytes=chr_size,
                chr_tiles=len(tiles),unique_chr_tiles=len(set(tiles)),
                verified_pixels=len(tiles)*64*2,plane_order_negative_rejected=rejected,
                proposed_vram_regions=regions,proposed_vram_bytes=sum(r['size'] for r in regions),
                actual_working_set_measured=False,fpga_fit_performed=False,
                snes_execution_tested=False,scenarios=scenarios)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=analyze(args.rom)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('mapper','chr_tiles','unique_chr_tiles','verified_pixels','proposed_vram_bytes')}))
