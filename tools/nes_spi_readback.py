# SPDX-License-Identifier: MIT
"""059 generated058 boot with internal SPI CHECK ownership and ordered ACK gate."""
import shutil
from nes_rom_readback import ROOT, PORTS, CONNECT, materialize as readback
from nes_rom_geometry import replace
from nes_spi_boot import put


def materialize(out):
    readback(out)
    shutil.copy2(ROOT/'src/nes/nes_rom_spi_check.sv',out/'nes_rom_spi.sv')
    s=(out/'nes_spi_boot.sv').read_text()
    s=replace(s,PORTS,'')
    s=replace(s,' wire load_begin,', ''' wire check_enable,check_request,check_ready,check_response,check_fault;
 wire [16:0] check_address,check_response_address;wire [7:0] check_data;
 wire load_begin,''')
    s=replace(s,'nes_rom_spi control(','nes_rom_spi_check control('+CONNECT)
    put(out/'nes_spi_boot.sv',s)
