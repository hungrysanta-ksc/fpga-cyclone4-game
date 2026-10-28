# SPDX-License-Identifier: MIT
"""Longer fixed-start capture schedule with group-local BG membership reuse."""
import shutil
import probe_nes_schedule369 as previous
from nes_lookup370 import apply
from nes_source368 import compile_arm
from nes_delta231 import ROOT
engine=previous.engine;old_build=engine.build_rom
def build(d):
 old_build(d);shutil.copyfile(d/'output.elf',d/'pre370-output.elf')
 apply(d);compile_arm(d)
 for n in ('nes_lookup370.py','probe_nes_lookup370.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n)
engine.build_rom=build;engine.__file__=__file__
if __name__=='__main__':engine.main()
