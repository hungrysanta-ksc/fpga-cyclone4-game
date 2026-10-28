# SPDX-License-Identifier: MIT
"""375 RTL with causal current/prior BG frontier selection on the actual M4."""
import shutil
import probe_nes_context375 as previous
from nes_frontier377 import apply
from nes_source368 import compile_arm
from nes_delta231 import ROOT
engine=previous.engine;old_build=engine.build_rom

def build(d):
 old_build(d);shutil.copyfile(d/'output.elf',d/'pre377-output.elf');apply(d);compile_arm(d)
 for n in ('nes_frontier377.py','probe_nes_frontier377.py'):shutil.copyfile(ROOT/'tools'/n,d/n)
engine.build_rom=build;engine.__file__=__file__
if __name__=='__main__':engine.main()
