# SPDX-License-Identifier: MIT
"""Matching whole Lite MAP of the common-record host;no FIT/STA claim."""
import map_nes_plan390 as previous
from nes_jobs394 import rtl
from probe_nes_jobs394_native import rom
from nes_delta231 import sha
old=previous.old.board
def board(d):
 old(d);rtl(d)
 p=d/'board.qsf';s=p.read_text();s='\n'.join(x for x in s.splitlines()if not any(n in x for n in('nes_tile_producer260.sv','nes_host_context375.sv')))
 p.write_text(s+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_tile_link394.sv\n',newline='\n')
 # Same4KiB physical ROM aperture;the actual candidate bytes are charged.
 q=d/'native394';q.mkdir();size,_=rom(q);assert size<=0xfc0
 image=(q/'spool.sfc').read_bytes();wire=image[:0xfc0]+image[0x7fc0:0x8000];assert len(wire)==4096
 (d/'sink-program.hex').write_text('\n'.join(f'{b:02x}'for b in wire)+'\n',newline='\n')
 previous.old.COMMON=tuple(n for n in previous.old.COMMON if n not in('nes_tile_producer260.sv','nes_host_context375.sv'))+('nes_tile_link394.sv',)
previous.old.board=board
if __name__=='__main__':previous.old.main()
