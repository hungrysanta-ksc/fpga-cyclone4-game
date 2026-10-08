# SPDX-License-Identifier: MIT
"""Materialize memory-inactive observation shell; no CF86 timing reuse."""
from pathlib import Path
import shutil
from nes_spi_boot import ROOT,put


def materialize(out):
    # Reuse only the established physical port declarations, not its logic.
    old=(ROOT/'src/nes/fxpak_nes_h1_top.sv').read_text()
    ports=old.split('module fxpak_nes_h1_top(',1)[1].split(');',1)[0]
    put(out/'fxpak_nes_diagnostic_top.sv','''// SPDX-License-Identifier: MIT
// CF87 observation-only physical shell. All memory/SNES data buses parked.
module fxpak_nes_diagnostic_top('''+ports+''');
 wire spi_miso,spi_drive;
 nes_clock_observation087 observe(.clk(CLKIN),.ref_clk(SNES_SYSCLK),
  .ss(SPI_SS),.sck(SPI_SCK),.mosi(SPI_MOSI),.miso(spi_miso),.drive(spi_drive),.ready(MCU_RDY));
 assign SPI_MISO=spi_drive?spi_miso:1'bz;
 assign ROM_ADDR=0;assign ROM_1CE=1;assign ROM_2CE=1;assign ROM_ZZ=1;
 assign ROM_OE=1;assign ROM_WE=1;assign ROM_BHE=1;assign ROM_BLE=1;assign ROM_DATA=16'hzzzz;
 assign RAM_ADDR=0;assign RAM_OE=1;assign RAM_WE=1;assign RAM_DATA=8'hzz;
 assign SNES_DATA=8'hzz;assign SNES_DATABUS_OE=1;assign SNES_DATABUS_DIR=0;
 assign DAC_MCLK=0;assign DAC_LRCK=0;assign DAC_SDOUT=0;assign SNES_IRQ=0;
endmodule
''')
    shutil.copy2(ROOT/'src/nes/diagnostic/nes_clock_observation087.sv',out/'nes_clock_observation087.sv')
    return ['nes_clock_observation087.sv','fxpak_nes_diagnostic_top.sv']
