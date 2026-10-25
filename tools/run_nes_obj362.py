# SPDX-License-Identifier: MIT
"""Actual M4 BG+OBJ packet from received block/previous ARM commit RAM."""
from pathlib import Path
from nes_delta231 import ROOT
if __name__=='__main__':
 s=(ROOT/'tools/run_nes_hint361.py').read_text()
 s=s.replace("probes/nes-hint360/arm03/decoder.elf","probes/nes-execute362/arm03/decoder.elf")
 s=s.replace(' extra=arm.instructions-before;', ''' arm.call('obj_reset362',[])
 for j in range(8):
  arm.call('obj_hint362',[0x20020000,epoch,serial-1,1])
  if int.from_bytes(arm.uc.mem_read(arm.symbols['obj_done362'],4),'little'):break
 n=arm.call('obj_packet362',[]);assert n==28
 packet=bytes(arm.uc.mem_read(arm.symbols['packet360'],n))
 extra=arm.instructions-before;''')
 s=s.replace('len(packet)==24 and packet[1]==5','len(packet)==28 and packet[1]==7')
 exec(compile(s,'run_obj362','exec'),dict(__name__='__main__',__file__=__file__))
