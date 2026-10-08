# SPDX-License-Identifier: MIT
"""Experimental CF85 physical shell; conditional dual-clock fault containment."""
from pathlib import Path
import argparse, shutil
from nes_diag_safety import materialize as base
from nes_rom_geometry import replace
from nes_spi_boot import ROOT, put


def materialize(out):
    files = base(out)
    name = 'nes_diag_clock_guard085.sv'
    shutil.copy2(ROOT/'src/nes/diagnostic'/name, out/name)
    files.append(name)
    path = out/'fxpak_nes_diagnostic_top.sv'
    source = replace(path.read_text(), 'wire memory_ready;', '''wire memory_ready;
 wire clock_allowed,clock_fault;
 nes_diag_clock_guard085 clock_guard(.mem_clk(CLKIN),.ref_clk(SNES_SYSCLK),
  .reset(!locked),.allow_memory(clock_allowed),.fault(clock_fault));''')
    source = replace(source, ".nes_reset(1'b0)", '.nes_reset(!clock_allowed)')
    put(path, source)
    path = out/'nes_h1_spi_boot.sv'
    put(path, replace(path.read_text(), "command==8'hcf ?8'h68", "command==8'hcf ?8'h85"))
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    materialize(args.out)
