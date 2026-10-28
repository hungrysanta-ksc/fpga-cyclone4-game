# SPDX-License-Identifier: MIT
"""Actual shared SPI/IRQ/ROM schedule using370 RTL and faster source decode."""
import shutil
import probe_nes_lookup370 as previous
from nes_frontier372 import apply
from nes_source368 import compile_arm
from nes_delta231 import ROOT
engine=previous.engine;old_build=engine.build_rom
def build(d):
 old_build(d);shutil.copyfile(d/'output.elf',d/'pre372-output.elf');apply(d);compile_arm(d)
 for n in ('nes_frontier372.py','probe_nes_frontier372.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
engine.build_rom=build;engine.__file__=__file__
if __name__=='__main__':engine.main()
