# SPDX-License-Identifier: MIT
"""057: expose the loader's accepted geometry register, no second configuration.

Frozen053/054 sources remain byte-identical. Materialized copies add only output
wires through loader/boot/SPI boot; the SPI argument latch is NOT the geometry.
"""
from pathlib import Path
import hashlib
from nes_spi_boot import ROOT, put

FILES = ['nes_rom_loader.sv', 'nes_rom_boot.sv', 'nes_spi_boot.sv']
PINNED = {
 'nes_rom_loader.sv': 'c2586db983738ed6dac324062b40cb83e25d1ef10a7a6e593788e4b92fcbacc8',
 'nes_rom_boot.sv': '9af83c3b3c88c02be465378706d5f830c3b9f4f10950871bc15856c8bf591c04',
 'nes_spi_boot.sv': '3e2f3aead4e8613bb207f240e7dfc3858ce7c1a84c52779a9866f662da2b3ffc',
}


def replace(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)


def materialize(out):
    for name in FILES:
        path = ROOT / 'src/nes' / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == PINNED[name], name
        s = path.read_text()
        if name == 'nes_rom_loader.sv':
            s = replace(s, ' output reg [16:0] loaded_bytes,',
                        ' output wire rom_chr32,\n output reg [16:0] loaded_bytes,')
            s = replace(s, ' wire [16:0] total=chr32?',
                        ' // Same accepted register drives length and core address mask.\n assign rom_chr32=chr32;\n wire [16:0] total=chr32?')
        else:
            s = replace(s, ' input wire rom_request,', ' output wire rom_chr32,\n input wire rom_request,')
            instance = 'nes_rom_loader loader(' if name == 'nes_rom_boot.sv' else 'nes_rom_boot boot('
            s = replace(s, instance, instance + '.rom_chr32(rom_chr32),')
        put(out / name, s)


def bind_core(s):
    s = replace(s, 'nes_spi_boot physical(', 'nes_spi_boot physical(.rom_chr32(chr_32k),')
    return s
