# SPDX-License-Identifier: MIT
import probe_nes_header399_native
import map_nes_joint398 as old
from nes_joint398 import rtl
from nes_fixed400 import apply
def fixed(d):rtl(d);apply(d)
old.prior.rtl=fixed
board=old.prior.previous.old.board
def current(d):
 board(d);p=d/'board.qsf';p.write_text(p.read_text()+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_read_owner400.sv\n',newline='\n')
 old.prior.previous.old.COMMON=tuple(old.prior.previous.old.COMMON)+('nes_read_owner400.sv',)
old.prior.previous.old.board=current
if __name__=='__main__':old.prior.previous.old.main()
