# SPDX-License-Identifier: MIT
"""Native word plan374 layered on unchanged dual-context373."""
import shutil,json
from nes_delta231 import ROOT,sha
from nes_dual373 import COMMON
DIRECTORY=ROOT/'src/fpga/nes_native374'
def materialize(d):
 shutil.copyfile(DIRECTORY/'nes_plan_batch206.sv',d/'nes_plan_batch206.sv')
def board(d):
 from nes_dual373 import board as old
 old(d);materialize(d)
