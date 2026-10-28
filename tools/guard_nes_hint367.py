# SPDX-License-Identifier: MIT
"""Reuse real cache/arbiter/STOP guards with the new shared SPI front end."""
from nes_delta231 import ROOT
if __name__=='__main__':
 import shutil
 from pathlib import Path
 from probe_nes_arm264 import crc
 native_copy=shutil.copyfile
 def copy_fixture(source,destination,*args,**kwargs):
  if Path(source).name!='hint361.hex':return native_copy(source,destination,*args,**kwargs)
  # This is a guard stimulus, not runtime production. The removed TB helper's
  # unexecuted default file still contains the historical five-tag ABI.
  packet=bytearray.fromhex('ea07030001000000030000007d1918191a1919191b19da13d813')
  packet.extend(crc(packet).to_bytes(2,'little'))
  Path(destination).write_text(packet.hex(' ')+'\n');return destination
 shutil.copyfile=copy_fixture
 s=(ROOT/'tools/guard_nes_obj362.py').read_text()
 s=s.replace('.progress_mode284(),','.source_mode367(),.progress_mode284(),')
 exec(compile(s,'guard_hint367','exec'),dict(__name__='__main__',__file__=__file__))
