# SPDX-License-Identifier: MIT
"""Retain all session/STOP/final ACK guards on the selected collector config."""
import shutil
from pathlib import Path
import guard_nes_capture365 as previous
from nes_delta231 import ROOT
if __name__=='__main__':
 previous.TB=previous.TB.replace('#(.EARLY_RELEASE(EARLY)) dut(', '#(.EARLY_RELEASE(EARLY),.REQUIRED_BITMAP(0)) dut(')
 native_copy=shutil.copyfile
 def copy(source,dest,*args,**kwargs):
  candidate=ROOT/'src/fpga/nes_source368'/Path(source).name
  return native_copy(candidate if candidate.exists() else source,dest,*args,**kwargs)
 shutil.copyfile=copy
 previous.main()
