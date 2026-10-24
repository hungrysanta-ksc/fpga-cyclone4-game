# SPDX-License-Identifier: MIT
"""338 RTL +352 decoder/material with fused compact geometry preparation."""
import os
# Accept the explicit fixed-start label as the existing fixed-phase switch.
if os.environ.get("NES319_FIXED")=="334.906436":os.environ["NES319_FIXED"]="1"
import probe_nes_raw352 as previous
from nes_compact354 import native
engine=previous.engine
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
