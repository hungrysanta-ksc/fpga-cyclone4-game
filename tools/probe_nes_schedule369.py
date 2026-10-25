# SPDX-License-Identifier: MIT
"""Run the NES368 fixed capture/ROM/IRQ schedule with demand-only classification."""
import shutil
import probe_nes_source368 as previous
from nes_schedule369 import apply
from nes_source368 import compile_arm
from nes_delta231 import ROOT
engine=previous.engine;old_build=engine.build_rom
def build(d):
 old_build(d);shutil.copyfile(d/'output.elf',d/'pre369-output.elf')
 apply(d);compile_arm(d)
 for n in ('nes_schedule369.py','probe_nes_schedule369.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n)
engine.build_rom=build;engine.__file__=__file__
if __name__=='__main__':engine.main()
