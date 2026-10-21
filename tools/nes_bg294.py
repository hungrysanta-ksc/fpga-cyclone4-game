# SPDX-License-Identifier: MIT
"""Compose stable BG publication with incremental native DMA dispatch."""
from nes_stage290 import prepare as staged
from nes_bg293 import apply_bg

def prepare(d):
    staged(d)
    apply_bg(d)
