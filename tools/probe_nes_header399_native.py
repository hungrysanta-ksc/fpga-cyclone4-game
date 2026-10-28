# SPDX-License-Identifier: MIT
"""Actual65816 component trial: DMA the immutable17B header into existing DP.
No new ABI, no additional SNES WRAM; not a live398/whole-board timing result.
"""
import inspect
import probe_nes_jobs394_native as old
from nes_delta231 import once

s=inspect.getsource(old.rom)
s=once(s," c.emit(0xa2,0,0);c.label('record394');c.absolute(0xbd,0x6080);c.absolute(0x9d,0x30);c.emit(0xe8,0xe0,17,0);c.branch(0xd0,'record394')",''' # Cartridge A-bus6080..6090 -> B-bus2180 -> existing WRAM0030..0040.
 # This is not WRAM-to-WRAM DMA. Keep the same17 bytes and all later checks.
 word(0x2181,0x30);c.store(0x2183,0);c.store(0x4300,0);c.store(0x4301,0x80)
 word(0x4302,0x6080);c.store(0x4304,0);word(0x4305,17);c.store(0x420b,1)''')
ns=dict(old.__dict__);exec(compile(s,'header399-native','exec'),ns);old.rom=ns['rom']
old.__doc__=__doc__
if __name__=='__main__':old.main()
