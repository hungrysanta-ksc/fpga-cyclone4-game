# SPDX-License-Identifier: MIT
"""Run IRQ guards on the BG ELF with the retained peripheral-only MMIO adapter."""
import guard_nes_irq284 as guards
from probe_nes_live287 import ARM

if __name__=='__main__':
    guards.ARM=ARM
    guards.main()
