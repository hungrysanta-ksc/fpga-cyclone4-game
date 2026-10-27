# SPDX-License-Identifier: MIT
"""Matching whole Lite of actual398 materialization; no isolated FSM cost."""
import argparse,sys,json
import map_nes_joint396 as prior
from nes_joint398 import rtl,ea_only
p=argparse.ArgumentParser(add_help=False);p.add_argument('--variant',choices=('joint','ea-only'),default='joint');variant,rest=p.parse_known_args();sys.argv=[sys.argv[0]]+rest
prior.rtl=rtl if variant.variant=='joint'else ea_only
board=prior.previous.old.board
def with_program(d):
 board(d)
 if variant.variant=='joint':
  p=d/'board.qsf';s=p.read_text();s+='\nset_global_assignment -name SYSTEMVERILOG_FILE nes_byte398.sv\n';p.write_text(s,newline='\n')
  prior.previous.old.COMMON=tuple(prior.previous.old.COMMON)+('nes_byte398.sv',)
prior.previous.old.board=with_program
if __name__=='__main__':prior.previous.old.main()
