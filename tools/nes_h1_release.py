# SPDX-License-Identifier: MIT
"""040: qualify ROMSEL abort by the raw active-read strobe.

Preserve the031 source and039 snapshot protocol. A completed response remains
output_valid until synchronized RD release; ROMSEL may legally be high then.
Premature release while pending and deselection during active RD still fault.
"""
from pathlib import Path
from nes_h1_spi import sha,replace
ROOT=Path(__file__).resolve().parents[1]
FRONTEND_SHA="c78ba887c2f1d8583513be6e98e990a09f7bd731cfd7cb7abc43c2e65e9a87bc"
def frontend():
 p=ROOT/'src/nes/nes_snes_frontend.sv'
 assert sha(p)==FRONTEND_SHA
 return replace(p.read_text(),
  'if((pending!=0 || output_valid) && is_payload(read_address) && romsel_n)',
  '//040: ROMSEL after completed raw RD release is idle, not an abort.\n   if((pending!=0 || output_valid) && is_payload(read_address) && !read_n && romsel_n)')
