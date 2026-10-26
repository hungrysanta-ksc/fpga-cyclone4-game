# SPDX-License-Identifier: MIT
"""Host shared header/cold-token sequencer and protected52B port375."""
import json,shutil
from nes_delta231 import ROOT,sha
from nes_dual373 import COMMON as OLD
DIRECTORY=ROOT/'src/fpga/nes_context375'
CHANGED=tuple(p.name for p in DIRECTORY.glob('*.sv'))
COMMON=tuple(dict.fromkeys(OLD+CHANGED))
def materialize(d):
 for n in CHANGED:shutil.copyfile(DIRECTORY/n,d/n)
def board(d):
 from nes_dual373 import board as previous
 previous(d);materialize(d)
 p=d/'board.qsf';s=p.read_text();line='set_global_assignment -name SYSTEMVERILOG_FILE nes_host_context375.sv'
 if line not in s:p.write_text(s+'\n'+line+'\n',newline='\n')
