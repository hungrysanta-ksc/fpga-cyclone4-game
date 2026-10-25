# SPDX-License-Identifier: MIT
"""Whole Quartus Lite MAP; new run encoder and single host packet position."""
import map_nes_ingress338 as previous
from nes_hybrid340 import apply,host
old_patch=previous.patch
def patch(d):old_patch(d);apply(d);host(d)
previous.engine.apply=patch
if __name__=='__main__':previous.engine.main()
