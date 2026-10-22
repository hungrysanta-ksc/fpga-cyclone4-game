# SPDX-License-Identifier: MIT
"""Actual65816 STOP-aware bank reuse; normal immutable522-command replay.

Every command polls sticky invalidation before packet DMA, after packet DMA,
after writes/zero DMA, and before ACK. STOP clears both bank flags and abandons
the command before acknowledging6006. Asynchronous STOP during an ACK is
rejected by the RTL gate and observed at the next poll.
"""
import inspect
import probe_nes_ordinary268 as old
from nes_delta231 import once


def rom(d,mode):
 s=inspect.getsource(old.rom)
 s=once(s," c.label('next');lda(0x6000);c.branch(0xf0,'next');", """ def check_stop():
  c.emit(0xe2,0x20);lda(0x6001);c.emit(0x29,0xc0);cond(0xd0,'stop')
 c.label('next');check_stop();lda(0x6000);cond(0xf0,'next');""")
 s=once(s," c.label('execute');c.emit", " c.label('execute');check_stop();c.emit")
 s=once(s," c.label('zero_done');c.emit", " c.label('zero_done');check_stop();c.emit")
 s=once(s," c.label('copied');c.emit(0xe2,0x20)", " c.label('copied');check_stop()")
 s=once(s," c.label('ack');c.store", " c.label('ack');check_stop();c.store")
 s=once(s,"c.jump('next');body=bytearray(c.finish());", """c.jump('next')
 c.label('stop');c.emit(0xe2,0x20);c.store(0x50,0);c.store(0x51,0)
 c.label('stop_wait');lda(0x6001);c.emit(0x29,0x80);c.branch(0xd0,'stop_wait')
 c.store(0x6006,0xa5);c.jump('next');body=bytearray(c.finish());""")
 s=s.replace('NES268 HDMA ZERO DMA ', 'NES269 STOP HDMA DMA ')
 ns=dict(old.__dict__);exec(compile(s,'rom269','exec'),ns);return ns['rom'](d,mode)


def main():
 lua=once(old.LUA,"if a==0x6000 then return", "if a==0x6001 then return event(0,a,0) elseif a==0x6000 then return")
 ns=dict(old.__dict__);ns.update(rom=rom,LUA=lua,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'ordinary269-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
