# SPDX-License-Identifier: MIT
"""Actual65816 STOP during OAM ROM DMA and nonmatching-pattern fallback.

Sticky endpoint status is modeled, not live FPGA/CPU co-simulation.
"""
import inspect
import guard_nes_stop269 as old
from probe_nes_oam279 import rom
from nes_delta231 import once


def main():
    lua = old.LUA.replace("0x7f6515,0x7f6518", "0x7f6200,0x7f6203")
    lua = lua.replace("0x16500+bank", "0x16200+bank")
    lua = once(lua, "emu.callbackType.read,ZERO_SOURCE)",
               "emu.callbackType.read,ZERO_SOURCE,ZERO_SOURCE+511)")
    source = inspect.getsource(old.main)
    a = source.index(" zero,bank1=")
    b = source.index(" (d/'packets.hex')", a)
    source = source[:a] + """ def packet(pattern=b'\\x00\\xf0\\x00\\x00',bank=0,count=512):
  b=bytearray(16);b[0]=8;b[1]=4;b[4:6]=(bank+1).to_bytes(2,'little')
  b[12:14]=len(pattern).to_bytes(2,'little');b[14:16]=count.to_bytes(2,'little')
  return bytes(b)+pattern
 zero,bank1=packet(),packet(bank=1)
 cases=[zero,bank1,packet(count=256),packet(b'\\x01\\x02\\x03\\x04',count=16),
        zero,bank1,packet(b'\\x91\\x92\\x93\\x94',count=16),zero,zero,bank1]
""" + source[b:]
    source = source.replace("labels['zero_dma']", "labels['oam_fill279']")
    source = source.replace("labels['zero_source']", "labels['template_source']")
    ns = dict(old.__dict__)
    ns.update(rom=rom, LUA=lua, __file__=__file__, __doc__=__doc__)
    exec(compile(source, "guard-oam279-main", "exec"), ns)
    ns["main"]()


if __name__ == "__main__":
    main()
