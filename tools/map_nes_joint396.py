# SPDX-License-Identifier: MIT
"""Whole Lite396 with identical storage/checker/source-plan execution boundary."""
import map_nes_plan390 as previous
from nes_joint396 import rtl
from probe_nes_jobs394_native import rom
old=previous.old.board
def board(d):
 old(d);rtl(d);p=d/'board.qsf';s=p.read_text();s='\n'.join(x for x in s.splitlines()if not any(n in x for n in('nes_tile_producer260.sv','nes_host_context375.sv')))
 for n in('nes_tile_link394.sv','nes_stage396.sv','nes_check396.sv','nes_walk396.sv'):s+='\nset_global_assignment -name SYSTEMVERILOG_FILE '+n
 p.write_text(s+'\n',newline='\n');q=d/'native396';q.mkdir();size,_=rom(q);assert size<=0xfc0;image=(q/'spool.sfc').read_bytes()
 (d/'sink-program.hex').write_text('\n'.join(f'{b:02x}'for b in image[:0xfc0]+image[0x7fc0:0x8000])+'\n',newline='\n')
 previous.old.COMMON=tuple(n for n in previous.old.COMMON if n not in('nes_tile_producer260.sv','nes_host_context375.sv'))+('nes_tile_link394.sv','nes_stage396.sv','nes_check396.sv','nes_walk396.sv')
previous.old.board=board
if __name__=='__main__':previous.old.main()
