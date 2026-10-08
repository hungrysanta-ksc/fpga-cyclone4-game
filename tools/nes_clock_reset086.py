# SPDX-License-Identifier: MIT
"""CF86: retain asynchronous cancellation, release reset only in memory domain."""
from nes_clock_guard085 import materialize as base
from nes_rom_geometry import replace
from nes_spi_boot import put


def materialize(out):
    files=base(out)
    path=out/'nes_h1_spi_boot.sv';s=path.read_text()
    s=replace(s,"command==8'hcf ?8'h85","command==8'hcf ?8'h86")
    s=replace(s,'.reset(memory_reset_raw),.ready(startup_ready)',
                '.reset(!memory_release[1]),.ready(startup_ready)')
    s=replace(s,'wire memory_reset=memory_reset_raw||!memory_release[1]||!startup_ready;',
                '''// CF86: memory_release asserts asynchronously when either watchdog
 // trips, even if CLKIN stops. Its deassertion is synchronized to CLKIN.
 // Do not OR raw cross-domain guard signals back into downstream control.
 wire memory_reset=!memory_release[1]||!startup_ready;''')
    put(path,s)
    return files
